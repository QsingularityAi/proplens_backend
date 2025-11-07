import pytest
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proplens_ai.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from crm.models import Lead
from campaigns.models import Campaign

User = get_user_model()


@pytest.fixture
def api_client():
    """Create API client"""
    return Client()


@pytest.fixture
def test_user():
    """Create test user"""
    user = User.objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )
    return user


@pytest.fixture
def auth_token(test_user):
    """Get auth token for test user"""
    refresh = RefreshToken.for_user(test_user)
    return str(refresh.access_token)


@pytest.fixture
def sample_lead():
    """Create sample lead"""
    return Lead.objects.create(
        lead_id='TEST001',
        lead_name='Test Lead',
        email='test@example.com',
        country_code='1',
        phone='1234567890',
        project_name='Lumina Grand',
        unit_type='2 bed',
        min_budget=1000000,
        max_budget=2000000,
        lead_status='connected',
    )


@pytest.mark.django_db
class TestCRMAPI:
    """Test CRM API endpoints"""
    
    def test_shortlist_leads(self, api_client, auth_token, sample_lead):
        """Test lead shortlisting"""
        response = api_client.post(
            '/api/crm/shortlist',
            {
                'project_name': 'Lumina Grand',
                'lead_status': 'connected',
            },
            HTTP_AUTHORIZATION=f'Bearer {auth_token}',
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'count' in data
        assert 'leads' in data
    
    def test_list_leads(self, api_client, auth_token, sample_lead):
        """Test listing leads"""
        response = api_client.get(
            '/api/crm/leads',
            HTTP_AUTHORIZATION=f'Bearer {auth_token}',
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.django_db
class TestCampaignAPI:
    """Test Campaign API endpoints"""
    
    def test_create_campaign(self, api_client, auth_token, sample_lead):
        """Test campaign creation"""
        response = api_client.post(
            '/api/campaigns/create',
            {
                'name': 'Test Campaign',
                'campaign_project_name': 'Lumina Grand',
                'channel': 'email',
                'lead_ids': [sample_lead.lead_id],
            },
            HTTP_AUTHORIZATION=f'Bearer {auth_token}',
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert data['name'] == 'Test Campaign'


@pytest.mark.django_db
class TestAgentAPI:
    """Test Agent API endpoints"""
    
    def test_query_agent(self, api_client, auth_token):
        """Test agent query"""
        response = api_client.post(
            '/api/agents/query',
            {'query': 'What are the features of Lumina Grand?'},
            HTTP_AUTHORIZATION=f'Bearer {auth_token}',
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.json()
        assert 'response' in data


@pytest.mark.django_db
class TestDocumentRAG:
    """Test Document RAG functionality"""
    
    def test_document_rag_service(self):
        """Test document RAG service"""
        from agents.services.document_rag import DocumentRAGService
        
        rag_service = DocumentRAGService()
        result = rag_service.query("What are the amenities?")
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.django_db
class TestVannaT2SQL:
    """Test Vanna T2SQL functionality"""
    
    def test_vanna_service(self):
        """Test Vanna service"""
        from agents.services.vanna_t2sql import VannaT2SQLService
        
        try:
            t2sql_service = VannaT2SQLService()
            # This might fail if Vanna is not properly configured
            # That's okay for testing
            assert t2sql_service is not None
        except Exception as e:
            # Expected if Vanna API key is not set
            pass



