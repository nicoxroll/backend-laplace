import os
import sys
from alembic import command
from alembic.config import Config

def run_migration():
    """Run database migrations using Alembic."""
    try:
        # Get the directory where this script is located
        basedir = os.path.abspath(os.path.dirname(__file__))
        
        # Create Alembic configuration object pointing to alembic.ini
        alembic_cfg = Config(os.path.join(basedir, "alembic.ini"))
        
        # Run the migration
        command.upgrade(alembic_cfg, "head")
        
        print("Migration completed successfully!")
        return True
    except Exception as e:
        print(f"Error during migration: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
