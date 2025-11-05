# Getting Started with Arcane Arsenal

## Step 1: Download the Project

You have the project at `/tmp/arcane-arsenal/`. You can either:

**Option A: Copy to your local directory**
```bash
cp -r /tmp/arcane-arsenal ~/arcane-arsenal
cd ~/arcane-arsenal
```

**Option B: Download the tarball**
```bash
# The tarball is at: /tmp/arcane-arsenal.tar.gz
# Download it and extract:
tar -xzf arcane-arsenal.tar.gz
cd arcane-arsenal
```

## Step 2: Create GitHub Repository

1. Go to https://github.com/new
2. Create a new repository named `arcane-arsenal`
3. **Do NOT initialize with README** (we already have one)
4. Click "Create repository"

## Step 3: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit: Project structure and documentation"

# Add your GitHub repo as remote (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/arcane-arsenal.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 4: Start Claude Code

Now you can use Claude Code to implement the project!

```bash
# Make sure you're in the project directory
cd arcane-arsenal

# Start Claude Code
claude-code
```

**Tell Claude Code:**
```
I want to implement Arcane Arsenal. Please read PROJECT_PLAN.md and CLAUDE_CODE_GUIDE.md, 
then start implementing Phase 1 following the step-by-step guide in CLAUDE_CODE_GUIDE.md.

Start with Step 1: Create src/core/result.py
```

## Step 5: Development Workflow

### Setting up your environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Running tests (after implementation)

```bash
pytest tests/
```

### Using the CLI (after implementation)

```bash
# Initialize a world
python -m src.cli.commands init my_world

# Create an entity
python -m src.cli.commands entity create my_world "Theron the Brave"

# List entities
python -m src.cli.commands entity list my_world
```

### Starting the web viewer (after implementation)

```bash
python -m src.web.server my_world
```

Then visit http://localhost:5000

## Project Structure

```
arcane-arsenal/
├── PROJECT_PLAN.md          # Complete architecture documentation
├── CLAUDE_CODE_GUIDE.md     # Step-by-step implementation guide
├── README.md                # Project overview
├── schema.sql               # Database schema
├── requirements.txt         # Dependencies
├── setup.py                 # Package configuration
├── .gitignore              # Git ignore rules
├── src/                    # Source code (to be implemented)
├── tests/                  # Tests (to be implemented)
└── worlds/                 # User world data
```

## Key Documents to Reference

1. **PROJECT_PLAN.md** - Read this for understanding the architecture
2. **CLAUDE_CODE_GUIDE.md** - Follow this for implementation order
3. **schema.sql** - Database schema reference

## Next Steps

After Phase 1 is complete:
- Character Manager module
- AI context generation
- Networking for multiplayer
- Additional game system modules

## Getting Help

All documentation is in the repository:
- Architecture details: PROJECT_PLAN.md
- Implementation guide: CLAUDE_CODE_GUIDE.md
- Database schema: schema.sql

## Tips for Claude Code

When starting Claude Code, make sure to:
1. Ask it to read PROJECT_PLAN.md first
2. Ask it to read CLAUDE_CODE_GUIDE.md for implementation order
3. Tell it to follow the steps sequentially
4. Ask it to write tests after each major component

Good luck! 🚀
