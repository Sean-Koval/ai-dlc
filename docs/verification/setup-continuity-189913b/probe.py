"""Disposable actual CLI walkthrough; no internal services or fixture monkeypatches."""
import datetime, hashlib, json, os, platform, subprocess, sys, time
from pathlib import Path

source=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
out.mkdir(parents=True,exist_ok=True)
workspace=out/'workspace'
workspace.mkdir(exist_ok=False)
env={k:os.environ[k] for k in ('PATH','LANG','LC_ALL','HOME','TMPDIR','SYSTEMROOT') if k in os.environ}
env.update(PYTHONPATH=str(source/'src'),PYTHONNOUSERSITE='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_TERMINAL_PROMPT='0',GIT_ALLOW_PROTOCOL='file')
for key,child in [('XDG_CONFIG_HOME','config'),('XDG_CACHE_HOME','cache'),('XDG_STATE_HOME','state'),('XDG_DATA_HOME','data')]:
 env[key]=str(workspace/child)
 (workspace/child).mkdir()
records=[]

def run(label,args,cwd=None,expected=0,extra=None):
 started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 t=time.monotonic()
 r=subprocess.run([str(x) for x in args],cwd=cwd or workspace,env={**env,**(extra or {})},capture_output=True,timeout=120)
 (out/f'{label}.stdout').write_bytes(r.stdout)
 (out/f'{label}.stderr').write_bytes(r.stderr)
 row={'label':label,'argv':[str(x) for x in args],'cwd':str(cwd or workspace),'started_at':started,'elapsed_seconds':time.monotonic()-t,'exit_code':r.returncode,'expected_exit_code':expected}
 records.append(row)
 (out/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 print(label,r.returncode,flush=True)
 if expected is not None and r.returncode!=expected: raise RuntimeError(f'{label} exit {r.returncode}; inspect capture')
 return r

def cli(label,*args,**kwargs): return run(label,[sys.executable,'-m','ai_dlc',*args],**kwargs)
def digest(b):return hashlib.sha256(b).hexdigest()
def snapshot(path):
 result={}
 for p in sorted(path.rglob('*')):
  if '.git' in p.relative_to(path).parts:continue
  if p.is_symlink():result[str(p.relative_to(path))]={'symlink':os.readlink(p)}
  elif p.is_file():result[str(p.relative_to(path))]={'sha256':digest(p.read_bytes()),'size':p.stat().st_size}
 return result
def save(name,data):(out/name).write_text(json.dumps(data,indent=2)+'\n')
def git(label,*args,cwd):return run(label,['git',*args],cwd)
def commit(label,path):
 git(label+'-add','add','.',cwd=path)
 git(label+'-commit','-c','user.name=Qualification Operator','-c','user.email=qualification@example.invalid','commit','-m',label,cwd=path)
 return git(label+'-revision','rev-parse','HEAD',cwd=path).stdout.decode().strip()

revision=run('engine-revision',['git','rev-parse','HEAD'],source).stdout.decode().strip()
status=run('engine-status',['git','status','--porcelain'],source).stdout.decode()
if revision!='189913b6cfc2c42828e35f4e2755c982b7f1e2da' or status:raise RuntimeError('Expected clean reviewed main189913b')
run('python-version',[sys.executable,'--version'])
run('git-version',['git','--version'])
cli('cli-help','--help')
save('environment.json',{'source':str(source),'commit':revision,'dirty':bool(status),'os':platform.system(),'version':platform.mac_ver()[0] if platform.system()=='Darwin' else platform.release(),'architecture':platform.machine(),'python':sys.executable,'xdg':{k:v for k,v in env.items() if k.startswith('XDG_')},'classification':'actual CLI on existing host with disposable runtime; not native model client','network_boundary':'No remote sources or providers configured; Git protocol restricted to file. No OS-wide network enforcement.','bootstrap':'Reuse prepared source interpreter; no bootstrap performed by this probe.'})
project=workspace/'project'
cli('adopt-preview','project','adopt','--root',project,'--preset','generic','--tracker','github-issues','--agent-client','codex','--agent-client','claude-code')
assert not project.exists()
cli('adopt-apply','project','adopt','--root',project,'--preset','generic','--tracker','github-issues','--agent-client','codex','--agent-client','claude-code','--apply')
(project/'authored-sentinel.txt').write_text('Qualification-owned authored application sentinel.\n')
profile=workspace/'profile-source'
profile.mkdir()
(profile/'ai-dlc-profile.toml').write_text('schema = 4\nprofile_id = "q01-local-profile"\n')
git('profile-init','init',cwd=profile)
profile_rev=commit('profile-v1',profile)
git('profile-tag','tag','reviewed-v1',cwd=profile)
cli('enroll-preview','machine','enroll',profile,'--profile-id','q01-local-profile','--machine-id','q01-disposable','--ref','reviewed-v1',cwd=project)
cli('enroll-apply','machine','enroll',profile,'--profile-id','q01-local-profile','--machine-id','q01-disposable','--ref','reviewed-v1','--apply',cwd=project)
cli('render-first','agents','render','--root',project,'--apply')
cli('render-first-check','agents','render','--root',project,'--check')
before=snapshot(project);local_before=snapshot(workspace/'config')
save('repeat-before.json',before)
cli('adopt-repeat','project','adopt','--root',project,'--preset','generic','--tracker','github-issues','--agent-client','codex','--agent-client','claude-code','--apply')
cli('enroll-repeat','machine','enroll',profile,'--profile-id','q01-local-profile','--machine-id','q01-disposable','--ref','reviewed-v1','--apply',cwd=project)
cli('render-repeat','agents','render','--root',project,'--apply')
cli('render-repeat-check','agents','render','--root',project,'--check')
after=snapshot(project);local_after=snapshot(workspace/'config')
save('repeat-after.json',after)
save('repeat-comparison.json',{'project_byte_identical':before==after,'local_config_byte_identical':local_before==local_after,'changed_project_paths':[p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)],'changed_config_paths':[p for p in local_before.keys()|local_after.keys() if local_before.get(p)!=local_after.get(p)]})
assert before==after and local_before==local_after
cli('readiness','project','readiness','--root',project,expected=None)
bundle=workspace/'bundle-source'
bundle.mkdir();git('bundle-init','init',cwd=bundle)
bundle_url='https://q01.example.invalid/bundle.git'
env.update(GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0=f'url.{bundle.as_uri()}.insteadOf',GIT_CONFIG_VALUE_0=bundle_url)
save('bundle-source-routing.json',{'declared_source':bundle_url,'actual_source':bundle.as_uri(),'method':'Task-local Git insteadOf rule and file-only protocol; no remote access or remote-portability claim.'})
def bundle_version(version,valid=True):
 content=f'---\nname: q01-continuity\ndescription: Use when inspecting the disposable Q01 continuity marker.\n---\n\n# Q01 local continuity\n\nQualification-authored marker version {version}; no external service.\n'.encode()
 p=bundle/'skills/continuity/SKILL.md';p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(content)
 manifest={'schema':1,'id':'q01-continuity','skills':{'q01-continuity':'skills/continuity/SKILL.md'},'templates':{},'files':{'skills/continuity/SKILL.md':digest(content) if valid else '0'*64}}
 (bundle/'bundle.json').write_text(json.dumps(manifest,indent=2)+'\n')
 rev=commit('bundle-'+version,bundle);git('bundle-tag-'+version,'tag',version,cwd=bundle)
 return rev,content
v1,content1=bundle_version('v1')
cli('bundle-preview-v1','agents','bundle','import',bundle_url,'--ref','v1','--id','q01-continuity','--root',project)
cli('bundle-apply-v1','agents','bundle','import',bundle_url,'--ref','v1','--id','q01-continuity','--root',project,'--apply','--expected-commit',v1)
config_path=project/'ai-dlc.toml'
config_before=config_path.read_text()
assert '[agents]' not in config_before
config_path.write_text(config_before+'\n[agents]\nbundles = ["q01-continuity"]\n')
save('bundle-selection.json',{'method':'Explicit authored selection in disposable project [agents].bundles after reviewed import; importer does not auto-select bundles.','config_sha256':digest(config_path.read_bytes())})
cli('bundle-render-v1','agents','render','--root',project,'--apply')
v2,content2=bundle_version('v2')
cli('bundle-preview-v2','agents','bundle','import',bundle_url,'--ref','v2','--id','q01-continuity','--root',project)
updated=cli('bundle-apply-v2','agents','bundle','import',bundle_url,'--ref','v2','--id','q01-continuity','--root',project,'--apply','--expected-commit',v2)
cli('bundle-render-v2','agents','render','--root',project,'--apply')
retained=json.loads(updated.stdout).get('retained_paths',[])
assert retained
save('retained-snapshots.json',{p:snapshot(project/p) for p in retained})
v3,_=bundle_version('v3-invalid',valid=False)
pre_invalid=snapshot(project)
cli('bundle-invalid-update','agents','bundle','import',bundle_url,'--ref','v3-invalid','--id','q01-continuity','--root',project,'--apply','--expected-commit',v3,expected=2)
assert pre_invalid==snapshot(project)
save('invalid-update-comparison.json',{'project_byte_identical':True,'meaning':'Invalid declared payload hash refused before publication; no induced mid-publication failure or rollback evidence.'})
owned=next(p for p in (project/'.agents/skills').rglob('SKILL.md') if p.read_bytes()==content2)
original=owned.read_bytes();owned.write_bytes(original+b'\nAuthored conflict marker added by qualification operator.\n')
conflict_before=snapshot(project)
conflicted=cli('authored-render-refusal','agents','render','--root',project,'--apply',expected=None)
assert conflicted.returncode!=0 and conflict_before==snapshot(project)
save('authored-conflict-comparison.json',{'path':str(owned.relative_to(project)),'before':conflict_before,'after':snapshot(project),'byte_identical':True})
owned.write_bytes(original)
save('deliberate-conflict-restoration.json',{'path':str(owned.relative_to(project)),'action':'Operator restores only its own deliberate appended marker to saved original bytes.','sha256':digest(original)})
bundle.rename(workspace/'bundle-source-unavailable')
profile.rename(workspace/'profile-source-unavailable')
(workspace/'cache').rename(workspace/'cache-retained-offline')
(workspace/'cache').mkdir()
# Enrollment requires its verified profile cache. Preserve that cache and disable
# access to both original Git sources; use a new empty cache only for bundle phase
# when the profile contract permits it. Actual failure is retained, never masked.
offline=cli('offline-empty-cache-render','agents','render','--root',project,'--check',expected=None)
if offline.returncode!=0:
 (workspace/'cache').rename(workspace/'cache-empty-retained')
 (workspace/'cache-retained-offline').rename(workspace/'cache')
cli('offline-fresh-render','agents','render','--root',project,'--check')
assert any(p.read_bytes()==content2 for p in (project/'.agents/skills').rglob('SKILL.md'))
assert any(p.read_bytes()==content2 for p in (project/'.claude/skills').rglob('SKILL.md'))
save('final-observations.json',{'commit':revision,'profile_revision':profile_rev,'bundle_revision':v2,'bundle_invalid_revision':v3,'repeat_byte_identical':True,'authored_conflict_preserved':True,'invalid_update_preserved':True,'retained_paths':retained,'fresh_process_bundle_bytes_match':True,'original_sources_absent':not bundle.exists() and not profile.exists(),'empty_cache_render_exit':offline.returncode,'limitations':['Prepared interpreter reused, no bootstrap or factory-clean claim.','Local original test inputs are deliberately authored but operations are actual CLI calls, not mocked services.','Invalid update refused before publication; failed publication/restore and race recovery remain unobserved operationally.','No native model/client session, remote provider, actual vault or human calibration.','No OS-wide network isolation; declared reserved HTTPS bundle URL routes to local file source via task-local Git insteadOf configuration; no remote portability proven.']})
save('cleanup-resources.json',{'workspace':str(workspace),'evidence':str(out),'retained_bundle_paths':[str(project/p) for p in retained],'note':'Nothing cleaned; inspect and remove only this entire disposable workspace after evidence is reviewed. Do not delete shared runtime.'})
print('PROBE COMPLETE',out,flush=True)
