"""
Tests for database migrations
"""
import pytest
import tempfile
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config


class TestMigrations:
    """Test Alembic migrations work correctly"""
    
    def test_migration_adds_progress_columns(self):
        """Test that running alembic upgrade head adds progress_percent and current_stage columns"""
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        try:
            # Setup database connection
            database_url = f"sqlite:///{temp_db_path}"
            engine = create_engine(database_url)
            
            # Configure Alembic
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            
            # Run migrations
            command.upgrade(alembic_cfg, "head")
            
            # Inspect the database schema
            inspector = inspect(engine)
            columns = inspector.get_columns('projects')
            column_names = [col['name'] for col in columns]
            
            # Assert both columns exist
            assert 'progress_percent' in column_names, "progress_percent column not found in projects table"
            assert 'current_stage' in column_names, "current_stage column not found in projects table"
            
            # Get column details
            progress_col = next(col for col in columns if col['name'] == 'progress_percent')
            stage_col = next(col for col in columns if col['name'] == 'current_stage')
            
            # Assert column properties
            assert not progress_col['nullable'], "progress_percent should be non-nullable"
            assert not stage_col['nullable'], "current_stage should be non-nullable"  
            assert progress_col['default'] == '0', f"progress_percent default should be '0', got {progress_col['default']}"
            assert 'initializing' in str(stage_col['default']), f"current_stage default should contain 'initializing', got {stage_col['default']}"
            
            print("✅ Migration test passed - both columns exist and are non-nullable with correct defaults")
            
        finally:
            # Cleanup
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)
    
    def test_project_insert_with_progress_fields(self):
        """Test that we can insert a project with progress fields after migration"""
        
        # Create temporary database  
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
            
        try:
            # Setup database connection
            database_url = f"sqlite:///{temp_db_path}"
            engine = create_engine(database_url)
            
            # Configure and run Alembic migrations
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", database_url)
            command.upgrade(alembic_cfg, "head")
            
            # Test inserting a project with progress fields
            Session = sessionmaker(bind=engine)
            with Session() as session:
                with session.begin():
                    # Insert a project with progress fields
                    result = session.execute(text("""
                        INSERT INTO projects (
                            id, user_email, project_label, filename, 
                            progress_percent, current_stage, status,
                            created_at, assumptions_collected
                        ) VALUES (
                            'test-migration-project', 'test@example.com', 
                            'Migration Test', 'test.pdf', 50, 'processing', 'pending',
                            datetime('now'), 1
                        )
                    """))
                    
                    # Verify the insert succeeded
                    project = session.execute(text("""
                        SELECT progress_percent, current_stage 
                        FROM projects 
                        WHERE id = 'test-migration-project'
                    """)).fetchone()
                    
                    assert project is not None, "Project insert failed"
                    assert project[0] == 50, f"Expected progress_percent=50, got {project[0]}"
                    assert project[1] == 'processing', f"Expected current_stage='processing', got {project[1]}"
                    
            print("✅ Project insert test passed - can insert and retrieve progress fields")
            
        finally:
            # Cleanup
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])