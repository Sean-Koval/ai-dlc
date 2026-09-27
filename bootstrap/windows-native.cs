// Cold-start boundary for PowerShell 5.1: no Python, shell tools, or path-following writes.
// Once the engine exists, selection uses its shared Windows storage transaction.
using System;
using System.IO;
using System.Collections.Generic;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;
using Microsoft.Win32.SafeHandles;

namespace AiDlc.Bootstrap {
    public sealed class DirectoryGuard : IDisposable {
        [StructLayout(LayoutKind.Sequential)] struct UnicodeString { public ushort Length, MaximumLength; public IntPtr Buffer; }
        [StructLayout(LayoutKind.Sequential)] struct ObjectAttributes { public int Length; public IntPtr Root, Name; public uint Attributes; public IntPtr Security, Quality; }
        [StructLayout(LayoutKind.Sequential)] struct IoStatus { public IntPtr Status, Information; }
        [StructLayout(LayoutKind.Sequential)] struct FileInformation {
            public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Created, Accessed, Written;
            public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
        }
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern SafeFileHandle CreateFileW(string p, uint a, uint s, IntPtr sec, uint c, uint f, IntPtr template);
        [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetFileInformationByHandle(SafeFileHandle h, out FileInformation i);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool GetVolumeInformationByHandleW(SafeFileHandle h, System.Text.StringBuilder name, int n, IntPtr serial, IntPtr max, IntPtr flags, System.Text.StringBuilder fs, int size);
        [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern uint GetDriveTypeW(string p);
        [DllImport("ntdll.dll")] static extern int NtCreateFile(out IntPtr h, uint a, ref ObjectAttributes o, out IoStatus io, IntPtr size, uint attrs, uint share, uint disposition, uint options, IntPtr ea, uint eaLength);
        [DllImport("ntdll.dll")] static extern int NtSetInformationFile(SafeFileHandle h, out IoStatus io, IntPtr data, uint size, int kind);
        [DllImport("ntdll.dll")] static extern uint RtlNtStatusToDosError(int status);
        [DllImport("advapi32.dll", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool ConvertStringSecurityDescriptorToSecurityDescriptorW(string text, uint rev, out IntPtr sd, IntPtr size);
        [DllImport("advapi32.dll")] static extern uint GetSecurityInfo(SafeFileHandle h, uint type, uint information, out IntPtr owner, IntPtr group, out IntPtr dacl, IntPtr sacl, out IntPtr sd);
        [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr sd);
        [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
        readonly Dictionary<string, Tuple<string,string>> created = new Dictionary<string, Tuple<string,string>>(StringComparer.OrdinalIgnoreCase);
        readonly List<SafeFileHandle> parents = new List<SafeFileHandle>();
        SafeFileHandle handle;
        public string PathName { get; private set; }
        static readonly string Sid = WindowsIdentity.GetCurrent().User.Value;
        static void Check(int result) { if (result < 0) throw new Win32Exception((int)RtlNtStatusToDosError(result)); }
        static void ValidName(string name) {
            if (String.IsNullOrEmpty(name) || name == "." || name == ".." || name.IndexOfAny(new char[]{'\\','/',':','\0'}) >= 0 || name.TrimEnd(' ','.') != name)
                throw new IOException("Unsafe native path component");
        }
        static void Validate(SafeFileHandle h, bool directory) {
            FileInformation i;
            if (!GetFileInformationByHandle(h, out i)) throw new Win32Exception();
            if ((i.Attributes & 0x400) != 0 || ((i.Attributes & 0x10) != 0) != directory || (!directory && i.Links != 1))
                throw new IOException("Reparse points, unexpected types, and hard links are refused");
        }
        static string Identity(SafeFileHandle h) {
            FileInformation value;
            if (!GetFileInformationByHandle(h,out value)) throw new Win32Exception();
            return value.Volume+":"+value.IndexHigh+":"+value.IndexLow;
        }
        static string Hash(byte[] value) { using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(value)); }
        static string Hash(SafeFileHandle value) {
            using(var borrowed = new SafeFileHandle(value.DangerousGetHandle(),false))
            using(var stream = new FileStream(borrowed,FileAccess.Read))
            using(var sha=SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(stream));
        }
        static void Private(SafeFileHandle h, bool trustedRuntimeOwner = false) {
            IntPtr owner, acl, descriptor;
            uint result = GetSecurityInfo(h, 1, 5, out owner, IntPtr.Zero, out acl, IntPtr.Zero, out descriptor);
            if (result != 0) throw new Win32Exception((int)result);
            try {
                byte[] raw = new byte[GetSecurityDescriptorLength(descriptor)];
                Marshal.Copy(descriptor, raw, 0, raw.Length);
                RawSecurityDescriptor security = new RawSecurityDescriptor(raw, 0);
                string ownerSid = security.Owner == null ? "absent" : security.Owner.Value;
                bool allowedOwner = ownerSid == Sid || (trustedRuntimeOwner && (ownerSid == "S-1-5-18" || ownerSid == "S-1-5-32-544"));
                if (!allowedOwner) throw new IOException("Unsafe bootstrap namespace owner: " + ownerSid + "; expected " + Sid + (trustedRuntimeOwner ? " or trusted runtime owner" : ""));
                if (security.DiscretionaryAcl == null) throw new IOException("Unsafe bootstrap namespace: null DACL");
                foreach (GenericAce ace in security.DiscretionaryAcl) {
                    if ((ace.AceFlags & AceFlags.InheritOnly) != 0) continue;
                    CommonAce common = ace as CommonAce;
                    if (common != null && common.AceQualifier == AceQualifier.AccessDenied) continue;
                    if (common == null || common.AceQualifier != AceQualifier.AccessAllowed ||
                        (common.SecurityIdentifier.Value != Sid && common.SecurityIdentifier.Value != "S-1-5-18" && common.SecurityIdentifier.Value != "S-1-5-32-544"))
                        throw new IOException("Unsafe bootstrap namespace DACL: " + (common == null ? "unsupported ACE" : common.SecurityIdentifier.Value));
                }
            } finally { LocalFree(descriptor); }
        }
        static SafeFileHandle Open(SafeFileHandle parent, string name, bool directory, uint access, uint share, uint disposition, bool privateObject) {
            ValidName(name);
            IntPtr text = Marshal.StringToHGlobalUni(name), u = IntPtr.Zero, descriptor = IntPtr.Zero;
            try {
                UnicodeString unicode = new UnicodeString { Length = checked((ushort)(name.Length*2)), MaximumLength = checked((ushort)(name.Length*2+2)), Buffer = text };
                u = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(UnicodeString))); Marshal.StructureToPtr(unicode,u,false);
                if (privateObject && !ConvertStringSecurityDescriptorToSecurityDescriptorW("O:"+Sid+"D:P(A;OICI;FA;;;"+Sid+")(A;OICI;FA;;;SY)",1,out descriptor,IntPtr.Zero)) throw new Win32Exception();
                ObjectAttributes attributes = new ObjectAttributes { Length = Marshal.SizeOf(typeof(ObjectAttributes)), Root = parent.DangerousGetHandle(), Name = u, Attributes = 0x1040, Security = descriptor };
                IntPtr raw; IoStatus io;
                Check(NtCreateFile(out raw, access | 0x100000, ref attributes, out io, IntPtr.Zero, 0, share, disposition, 0x200020u | (directory ? 1u : 0x40u), IntPtr.Zero, 0));
                SafeFileHandle result = new SafeFileHandle(raw,true);
                try { Validate(result,directory); if (privateObject) Private(result); return result; } catch { result.Dispose(); throw; }
            } finally { Marshal.FreeHGlobal(text); if(u != IntPtr.Zero) Marshal.FreeHGlobal(u); if(descriptor != IntPtr.Zero) LocalFree(descriptor); }
        }
        public DirectoryGuard(string path, bool create, bool privateDirectory) : this(path,create,privateDirectory,false) { }
        public static DirectoryGuard OpenRuntimeDirectory(string path) {
            // A verified native installer can inherit an Administrators/SYSTEM owner.
            // This read-only runtime boundary still requires the same restricted DACL.
            return new DirectoryGuard(path,false,true,true);
        }
        private DirectoryGuard(string path, bool create, bool privateDirectory, bool trustedRuntimeOwner) {
            PathName = System.IO.Path.GetFullPath(path).TrimEnd('\\');
            if (PathName.StartsWith("\\") || PathName.Length < 3) throw new IOException("Bootstrap requires an absolute local NTFS path");
            string root = System.IO.Path.GetPathRoot(PathName);
            if (GetDriveTypeW(root) != 3) throw new IOException("Bootstrap requires a local fixed NTFS drive");
            try {
                handle = CreateFileW(root,0x20081,3,IntPtr.Zero,3,0x02200000,IntPtr.Zero);
                if(handle.IsInvalid) throw new Win32Exception();
                parents.Add(handle); Validate(handle,true);
                var fs = new System.Text.StringBuilder(64);
                if (!GetVolumeInformationByHandleW(handle,null,0,IntPtr.Zero,IntPtr.Zero,IntPtr.Zero,fs,64) || fs.ToString() != "NTFS") throw new IOException("Bootstrap requires local NTFS");
                string[] parts = PathName.Substring(root.Length).Split(new char[]{'\\'},StringSplitOptions.RemoveEmptyEntries);
                for (int index=0; index<parts.Length; index++) {
                    bool final = index == parts.Length-1;
                    try { handle = Open(handle,parts[index],true,0x20081,3,1,final && privateDirectory && !trustedRuntimeOwner); }
                    catch (Win32Exception error) {
                        if (!create || (error.NativeErrorCode != 2 && error.NativeErrorCode != 3)) throw;
                        handle = Open(handle,parts[index],true,0x20081,3,2,true);
                    }
                    parents.Add(handle);
                }
                if(privateDirectory) Private(handle,trustedRuntimeOwner);
            } catch { Dispose(); throw; }
        }
        public FileStream OpenRead(string name) { return new FileStream(Open(handle,name,false,0x80020000,1,1,false),FileAccess.Read); }
        public byte[] Read(string name) { using(var source=OpenRead(name)) using(var target=new MemoryStream()) { source.CopyTo(target); return target.ToArray(); } }
        public void WriteNew(string name, byte[] bytes) {
            using(var stream=new FileStream(Open(handle,name,false,0xC0020000,1,2,true),FileAccess.ReadWrite)) {
                stream.Write(bytes,0,bytes.Length); stream.Flush(true);
                created[name]=Tuple.Create(Identity(stream.SafeFileHandle),Hash(bytes));
            }
        }
        public FileStream ProtectForExecution() {
            // NTFS mount-point mutation requires an empty directory. Keep a private
            // child open without delete sharing while external tools use lexical paths.
            string name = ".bootstrap-execution-" + Guid.NewGuid().ToString("N");
            WriteNew(name,new byte[]{1});
            return OpenRead(name);
        }
        public FileStream Lock(string name) { return new FileStream(Open(handle,name,false,0xC0020000,0,3,true),FileAccess.ReadWrite); }
        public void Publish(string source, DirectoryGuard destination, string name, bool replace) {
            ValidName(name);
            using(var file=Open(handle,source,false,0x80030000,1,1,true)) {
                Tuple<string,string> owned;
                if (!created.TryGetValue(source,out owned) || Identity(file) != owned.Item1 || Hash(file) != owned.Item2)
                    throw new IOException("Bootstrap stage identity or digest changed; preserved for inspection");
                // Native FILE_RENAME_INFORMATION uses a relative target and held directory handle.
                byte[] text = System.Text.Encoding.Unicode.GetBytes(name);
                int rootOffset = IntPtr.Size == 8 ? 8 : 4, lengthOffset = rootOffset+IntPtr.Size, nameOffset = lengthOffset+4;
                int size = Math.Max(nameOffset+text.Length+2,IntPtr.Size == 8 ? 32 : 16);
                IntPtr data=Marshal.AllocHGlobal(size);
                try {
                    Marshal.Copy(new byte[size],0,data,size); Marshal.WriteInt32(data,replace?1:0); Marshal.WriteIntPtr(data,rootOffset,destination.handle.DangerousGetHandle());
                    Marshal.WriteInt32(data,lengthOffset,text.Length); Marshal.Copy(text,0,IntPtr.Add(data,nameOffset),text.Length); IoStatus io;
                    Check(NtSetInformationFile(file,out io,data,(uint)size,10));
                    created.Remove(source); destination.created[name]=owned;
                } finally { Marshal.FreeHGlobal(data); }
            }
        }
        public void Dispose() { for(int i=parents.Count-1;i>=0;i--) parents[i].Dispose(); parents.Clear(); }
    }
}
