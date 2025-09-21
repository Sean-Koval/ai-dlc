use anyhow::Context;
use clap::{Parser, Subcommand};
use include_dir::{Dir, DirEntry, include_dir};
use std::ffi::OsStr;
use std::path::Path;

// Embed provider templates directly from the crate so published packages
// include the full asset set.
static TEMPLATES_DIR: Dir = include_dir!("$CARGO_MANIFEST_DIR/embedded-templates");

#[derive(Parser, Debug)]
#[command(version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand, Debug)]
enum Commands {
    Scaffold(ScaffoldArgs),
}

#[derive(Parser, Debug)]
struct ScaffoldArgs {
    #[arg(long, short)]
    provider: Vec<String>,
    #[arg(long)]
    all: bool,
}

fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt::init();
    let cli = Cli::parse();
    match cli.command {
        Commands::Scaffold(args) => handle_scaffold(args)?,
    }
    Ok(())
}

fn handle_scaffold(args: ScaffoldArgs) -> anyhow::Result<()> {
    tracing::info!("Scaffolding templates...");

    let providers_to_scaffold = if args.all {
        TEMPLATES_DIR
            .dirs()
            .map(|d| d.path().to_str().unwrap().to_string())
            .collect()
    } else if args.provider.is_empty() {
        tracing::warn!("No providers specified. Use --provider or --all. Exiting.");
        return Ok(());
    } else {
        args.provider
    };

    tracing::info!("Scaffolding for providers: {:?}", providers_to_scaffold);

    for provider_name in providers_to_scaffold {
        if let Some(provider_dir) = TEMPLATES_DIR.get_dir(&provider_name) {
            let hidden_dir_name = format!(".{}", provider_name);
            let strip_prefix = provider_dir.path();

            for dir in provider_dir.dirs() {
                tracing::debug!(path = ?dir.path(), "provider subdir detected");
            }

            let target_name = OsStr::new(&hidden_dir_name);
            let hidden_dir = provider_dir
                .dirs()
                .find(|dir| dir.path().file_name() == Some(target_name));

            if let Some(hidden_dir) = hidden_dir {
                tracing::info!(
                    "Creating hidden provider directory: {} in current working directory",
                    hidden_dir_name
                );
                extract_dir(hidden_dir, Path::new("."), strip_prefix)?;
            } else {
                tracing::warn!(
                    "Provider '{}' does not contain '{}'; skipping.",
                    provider_name,
                    hidden_dir_name
                );
            }
        } else {
            tracing::warn!(
                "Provider '{}' not found in embedded templates.",
                provider_name
            );
        }
    }

    tracing::info!("Scaffolding complete.");
    Ok(())
}

fn extract_dir(embedded_dir: &Dir, dest_root: &Path, strip_prefix: &Path) -> anyhow::Result<()> {
    let relative_dir = embedded_dir
        .path()
        .strip_prefix(strip_prefix)
        .unwrap_or_else(|_| embedded_dir.path());
    let dir_path = dest_root.join(relative_dir);
    std::fs::create_dir_all(&dir_path)
        .with_context(|| format!("Failed to create directory: {:?}", dir_path))?;

    for entry in embedded_dir.entries() {
        let relative_path = entry
            .path()
            .strip_prefix(strip_prefix)
            .unwrap_or_else(|_| entry.path());
        let path = dest_root.join(relative_path);
        match entry {
            DirEntry::Dir(d) => {
                extract_dir(d, dest_root, strip_prefix)?;
            }
            DirEntry::File(f) => {
                if let Some(parent) = path.parent() {
                    std::fs::create_dir_all(parent).with_context(|| {
                        format!("Failed to create parent directory: {:?}", parent)
                    })?;
                }
                tracing::debug!("Writing file: {:?}", path);
                std::fs::write(&path, f.contents())
                    .with_context(|| format!("Failed to write file: {:?}", path))?;
            }
        }
    }
    Ok(())
}
