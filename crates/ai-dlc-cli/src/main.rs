use anyhow::Context;
use clap::{Parser, Subcommand};
use include_dir::{include_dir, Dir, DirEntry};
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
        TEMPLATES_DIR.dirs().map(|d| d.path().to_str().unwrap().to_string()).collect()
    } else if args.provider.is_empty() {
        tracing::warn!("No providers specified. Use --provider or --all. Exiting.");
        return Ok(());
    } else {
        args.provider
    };

    tracing::info!("Scaffolding for providers: {:?}", providers_to_scaffold);

    for provider_name in providers_to_scaffold {
        if let Some(provider_dir) = TEMPLATES_DIR.get_dir(&provider_name) {
            let base_path = Path::new("templates");
            tracing::info!("Creating templates for provider: {}", provider_name);
            extract_dir(provider_dir, base_path)?;
        } else {
            tracing::warn!("Provider '{}' not found in embedded templates.", provider_name);
        }
    }

    tracing::info!("Scaffolding complete.");
    Ok(())
}

fn extract_dir(embedded_dir: &Dir, base_path: &Path) -> anyhow::Result<()> {
    let dir_path = base_path.join(embedded_dir.path());
    std::fs::create_dir_all(&dir_path)
        .with_context(|| format!("Failed to create directory: {:?}", dir_path))?;

    for entry in embedded_dir.entries() {
        let path = base_path.join(entry.path());
        match entry {
            DirEntry::Dir(d) => {
                extract_dir(d, base_path)?;
            }
            DirEntry::File(f) => {
                tracing::debug!("Writing file: {:?}", path);
                std::fs::write(&path, f.contents())
                    .with_context(|| format!("Failed to write file: {:?}", path))?;
            }
        }
    }
    Ok(())
}
