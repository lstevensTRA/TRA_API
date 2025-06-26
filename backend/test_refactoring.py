#!/usr/bin/env python3
"""
Test script to verify the refactored modules work correctly.
"""

def test_imports():
    """Test that all modules can be imported successfully."""
    try:
        print("Testing imports...")
        
        # Test basic imports
        from app.routes import health, auth, data, income_comparison, transcript_routes
        print("✅ All route modules imported successfully")
        
        # Test server import
        from server import app
        print("✅ Server app imported successfully")
        
        # Test that routers are accessible
        print(f"✅ Health router: {health.router}")
        print(f"✅ Auth router: {auth.router}")
        print(f"✅ Data router: {data.router}")
        print(f"✅ Income comparison router: {income_comparison.router}")
        print(f"✅ Transcript routes router: {transcript_routes.router}")
        
        # Test that app has the routers
        print(f"✅ App routes count: {len(app.routes)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_income_comparison_endpoint():
    """Test that the income comparison endpoint is registered."""
    try:
        from server import app
        
        # Look for the income comparison endpoint
        income_comparison_routes = [route for route in app.routes if hasattr(route, 'path') and 'income-comparison' in route.path]
        
        if income_comparison_routes:
            print(f"✅ Income comparison endpoint found: {income_comparison_routes[0].path}")
            return True
        else:
            print("❌ Income comparison endpoint not found")
            return False
            
    except Exception as e:
        print(f"❌ Endpoint test failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 Testing refactored modules...")
    
    import_success = test_imports()
    endpoint_success = test_income_comparison_endpoint()
    
    if import_success and endpoint_success:
        print("\n🎉 All tests passed! Refactoring successful.")
    else:
        print("\n❌ Some tests failed. Check the errors above.") 