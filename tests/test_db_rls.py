import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DB_URL = os.getenv("TEST_DB_URL", "postgresql://levi_admin:levi_secure_pw@localhost:5432/levi_test")

@pytest.fixture(scope="module")
def rls_engine():
    try:
        engine = create_engine(DB_URL, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("CREATE TABLE IF NOT EXISTS tenant_data (id SERIAL PRIMARY KEY, tenant_id VARCHAR, data VARCHAR)"))
            conn.execute(text("ALTER TABLE tenant_data ENABLE ROW LEVEL SECURITY"))
            conn.execute(text("DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_data"))
            conn.execute(text("CREATE POLICY tenant_isolation_policy ON tenant_data FOR ALL TO PUBLIC USING (tenant_id = current_setting('app.current_tenant', true))"))
            
            # Seed data
            conn.execute(text("TRUNCATE TABLE tenant_data"))
            conn.execute(text("INSERT INTO tenant_data (tenant_id, data) VALUES ('tenant_A', 'secret_A')"))
            conn.execute(text("INSERT INTO tenant_data (tenant_id, data) VALUES ('tenant_B', 'secret_B')"))
            conn.commit()
    except Exception as e:
        pytest.skip(f"Could not connect or setup RLS test DB: {e}")
    
    yield engine
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS tenant_data CASCADE"))
        conn.commit()

def test_rls_blocks_cross_tenant_read(rls_engine):
    with rls_engine.connect() as conn:
        # Simulate connecting as tenant_A
        conn.execute(text("SET app.current_tenant = 'tenant_A'"))
        result = conn.execute(text("SELECT data FROM tenant_data")).fetchall()
        
        # Should only see tenant_A's data
        assert len(result) == 1
        assert result[0][0] == 'secret_A'
        
        # Simulate connecting as tenant_B
        conn.execute(text("SET app.current_tenant = 'tenant_B'"))
        result = conn.execute(text("SELECT data FROM tenant_data")).fetchall()
        
        # Should only see tenant_B's data
        assert len(result) == 1
        assert result[0][0] == 'secret_B'
        
        # Connecting without context (system bypass or unauthenticated) depending on policy
        conn.execute(text("RESET app.current_tenant"))
        result = conn.execute(text("SELECT data FROM tenant_data")).fetchall()
        
        # Default policy blocks all if tenant not set
        assert len(result) == 0
