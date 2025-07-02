import requests
import json

BASE_URL = 'http://127.0.0.1:8000'

# List of endpoints to test (method, path, sample_payload, description)
ENDPOINTS = [
    # Auth
    ('POST', '/auth/login', {'username': 'test', 'password': 'test'}, 'Login (should fail with test creds)'),
    ('GET', '/auth/status', None, 'Auth status'),
    ('POST', '/auth/logout', None, 'Logout'),
    # Health
    ('GET', '/health/', None, 'Health check'),
    # Pattern Learning
    ('GET', '/pattern-learning/stats', None, 'Pattern learning stats'),
    ('GET', '/pattern-learning/suggestions', None, 'Pattern suggestions'),
    ('POST', '/pattern-learning/feedback', {'extraction_id': 'dummy', 'is_correct': True}, 'Pattern feedback (should fail w/ dummy)'),
    ('GET', '/pattern-learning/patterns', None, 'Pattern performance'),
    ('GET', '/pattern-learning/extractions', None, 'Pattern extractions'),
    ('GET', '/pattern-learning/health', None, 'Pattern learning health'),
    # Case Management
    ('GET', '/case-management/logs', None, 'Case management logs'),
    # Health
    ('GET', '/health/', None, 'Health check'),
    # TODO: Add more endpoints and sample payloads as needed
]

def test_endpoint(method, path, payload=None):
    url = BASE_URL + path
    try:
        if method == 'GET':
            resp = requests.get(url)
        elif method == 'POST':
            resp = requests.post(url, json=payload)
        else:
            print(f'Unsupported method: {method}')
            return False
        if resp.status_code == 200:
            print(f'✅ {method} {path} - PASS')
            try:
                resp.json()
            except Exception:
                print(f'   ⚠️  {method} {path} - Response not JSON')
            return True
        else:
            print(f'❌ {method} {path} - FAIL (Status {resp.status_code})')
            print(f'   Response: {resp.text[:200]}')
            return False
    except Exception as e:
        print(f'❌ {method} {path} - ERROR: {e}')
        return False

def main():
    print('--- Automated Endpoint QA/QC ---')
    passed = 0
    failed = 0
    for method, path, payload, desc in ENDPOINTS:
        print(f'\nTesting: {desc}')
        if test_endpoint(method, path, payload):
            passed += 1
        else:
            failed += 1
    print(f'\n--- Summary ---')
    print(f'Passed: {passed}')
    print(f'Failed: {failed}')
    print('--- End of Report ---')

if __name__ == '__main__':
    main() 