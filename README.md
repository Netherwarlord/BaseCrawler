# BaseCrawler

A custom built database management tool written in Python with a modern GUI. This tool provides a fast and lightweight alternative to pgAdmin 4, supporting multiple database types.

## Features

- **Multi-Database Support**: PostgreSQL, MongoDB, MariaDB, and MySQL
- **Modern GUI**: Built with CustomTkinter for a sleek user interface
- **Lightweight**: Faster and more responsive than traditional tools
- **Connection Management**: Save and manage multiple database connections

## Installation

### Windows

Download the latest Windows installer from the [Releases](https://github.com/Netherwarlord/BaseCrawler/releases) page and run the setup executable.

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/Netherwarlord/BaseCrawler.git
   cd BaseCrawler
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python app.py
   ```

## CI/CD Pipeline

This project uses GitHub Actions to automatically build Windows installers on every push to the main branch and on tagged releases.

### Automated Builds

- **On Push to Main**: Builds a development version with commit hash
- **On Tag (v*.*.*)**: Builds a release version and creates a GitHub release
- **Manual Trigger**: Can be triggered manually via workflow_dispatch

### Build Process

1. Sets up Python 3.11 environment
2. Installs all dependencies from requirements.txt
3. Uses PyInstaller to create a standalone Windows executable
4. Creates a Windows installer using Inno Setup
5. Uploads the installer as an artifact (available for 90 days)
6. For tagged releases, automatically creates a GitHub release with the installer

### Creating a Release

To create a new release:

1. Update the version in your code (if applicable)
2. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. The CI/CD pipeline will automatically build and publish the release

### Artifacts

Build artifacts are available for 90 days after each build. You can download them from the Actions tab on GitHub.

## Development

### Requirements

- Python 3.11 or higher
- Dependencies listed in requirements.txt

### Building Locally

To build the Windows executable locally:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "BaseCrawler" app.py
```

The executable will be created in the `dist/` directory.

## License

See the [LICENSE](LICENSE) file for details.