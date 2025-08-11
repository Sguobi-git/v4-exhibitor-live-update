# app.py - Updated with Direct Google Sheets Integration
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import logging
import os
import json

# Import the Direct Google Sheets manager (no Abacus AI)
from direct_google_sheets_manager import DirectGoogleSheetsManager

# Initialize Flask app with static folder for React build
app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)  # Enable CORS for React app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SMART CACHING SYSTEM - Allows manual refresh override
CACHE = {}
CACHE_DURATION = 30  # 30 seconds cache for frequent updates (like your Streamlit app)
FORCE_REFRESH_PARAM = 'force_refresh'

def get_from_cache(key, allow_cache=True):
    if not allow_cache:
        logger.info(f"Cache bypassed for {key} (manual refresh)")
        return None
        
    if key in CACHE:
        data, timestamp = CACHE[key]
        if datetime.now() - timestamp < timedelta(seconds=CACHE_DURATION):
            logger.info(f"Using cached data for {key}")
            return data
    return None

def set_cache(key, data):
    CACHE[key] = (data, datetime.now())
    logger.info(f"Cached data for {key}")

# Initialize Google Sheets Manager with environment credentials
def get_credentials():
    """Get Google credentials from environment variable or file"""
    try:
        # Try to get credentials from environment variable first
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            # Parse the JSON string and create a temporary file
            credentials_dict = json.loads(credentials_json)
            
            # Create temporary credentials file
            with open('/tmp/credentials.json', 'w') as f:
                json.dump(credentials_dict, f)
            return '/tmp/credentials.json'
        else:
            # Fallback to local file (for development)
            return 'credentials.json'
    except Exception as e:
        logger.error(f"Error setting up credentials: {e}")
        return None

# Initialize Direct Google Sheets Manager
credentials_path = get_credentials()
if credentials_path:
    gs_manager = DirectGoogleSheetsManager(credentials_path)
else:
    gs_manager = None
    logger.warning("No valid credentials found - using mock data only")

# Your Google Sheet ID - NOW SUPPORTS MULTIPLE SHEETS!
SHEET_ID = "1_yBu2Rx4UGcSL04r0aAMyZDHbpuTKrJK9KavEeanZXs"  # Your new sheet with multiple sheets

# Mock data for testing (fallback when Google Sheets unavailable)
def get_mock_orders():
    return [
        {
            'id': 'ORD-2025-001',
            'booth_number': 'A-245',
            'exhibitor_name': 'TechFlow Innovations',
            'item': 'Premium Booth Setup Package',
            'description': 'Complete booth installation with premium furniture, lighting, and tech setup',
            'color': 'White',
            'quantity': 1,
            'status': 'out-for-delivery',
            'order_date': 'June 14, 2025',
            'comments': 'Rush delivery requested',
            'section': 'Section A'
        },
        {
            'id': 'ORD-2025-002',
            'booth_number': 'A-245',
            'exhibitor_name': 'TechFlow Innovations',
            'item': 'Interactive Display System',
            'description': '75" 4K touchscreen display with interactive software and mounting',
            'color': 'Black',
            'quantity': 1,
            'status': 'in-route',
            'order_date': 'June 13, 2025',
            'comments': '',
            'section': 'Section A'
        }
    ]

def load_orders_from_sheets(force_refresh=False):
    """Load orders from Google Sheets with smart caching - SUPPORTS MULTIPLE SHEETS"""
    cache_key = "all_orders"
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return cached_data
    
    try:
        if not gs_manager:
            logger.warning("No Google Sheets manager available, using mock data")
            mock_data = get_mock_orders()
            set_cache(cache_key, mock_data)
            return mock_data
            
        # Get all orders from ALL sheets (main + sections) - MULTIPLE SHEETS SUPPORT!
        all_orders = gs_manager.get_all_orders(SHEET_ID)
        
        if all_orders:
            set_cache(cache_key, all_orders)
            if force_refresh:
                logger.info("🔄 FORCE REFRESH: Fresh data loaded from Google Sheets (multiple sheets)")
            return all_orders
        
        logger.warning("No data found in Google Sheets, using mock data")
        mock_data = get_mock_orders()
        set_cache(cache_key, mock_data)
        return mock_data
        
    except Exception as e:
        logger.error(f"Error loading orders from sheets: {e}")
        logger.info("Falling back to mock data")
        mock_data = get_mock_orders()
        set_cache(cache_key, mock_data)
        return mock_data

def load_exhibitors_from_sheets(force_refresh=False):
    """Load exhibitors from Google Sheets with smart caching - SUPPORTS MULTIPLE SHEETS"""
    cache_key = "exhibitors"
    
    # Check cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return cached_data
    
    try:
        if not gs_manager:
            logger.warning("No Google Sheets manager available, using fallback")
            fallback_exhibitors = [
                { name: 'VIVA ABACUS', booth: '9999', total_orders: 1, delivered_orders: 0 }
            ]
            set_cache(cache_key, fallback_exhibitors)
            return fallback_exhibitors
            
        # Get all exhibitors from ALL sheets - MULTIPLE SHEETS SUPPORT!
        exhibitors = gs_manager.get_all_exhibitors(SHEET_ID)
        
        if exhibitors:
            set_cache(cache_key, exhibitors)
            if force_refresh:
                logger.info("🔄 FORCE REFRESH: Fresh exhibitors loaded from Google Sheets (multiple sheets)")
            return exhibitors
        
        logger.warning("No exhibitors found in Google Sheets, using fallback")
        fallback_exhibitors = [
            { name: 'VIVA ABACUS', booth: '9999', total_orders: 1, delivered_orders: 0 }
        ]
        set_cache(cache_key, fallback_exhibitors)
        return fallback_exhibitors
        
    except Exception as e:
        logger.error(f"Error loading exhibitors from sheets: {e}")
        fallback_exhibitors = [
            { name: 'VIVA ABACUS', booth: '9999', total_orders: 1, delivered_orders: 0 }
        ]
        set_cache(cache_key, fallback_exhibitors)
        return fallback_exhibitors

# REACT APP SERVING ROUTES
@app.route('/')
def serve_react_app():
    """Serve the React app"""
    try:
        return send_file('frontend/build/index.html')
    except FileNotFoundError:
        return "Frontend not built. Please run 'npm run build' in frontend directory.", 404

@app.route('/<path:path>')
def serve_static_files(path):
    """Serve static files or React app for client-side routing"""
    try:
        # Try to serve static file first
        return send_from_directory('frontend/build', path)
    except FileNotFoundError:
        # If file not found, serve React app (for client-side routing)
        try:
            return send_file('frontend/build/index.html')
        except FileNotFoundError:
            return "Frontend not built. Please run 'npm run build' in frontend directory.", 404

# API ROUTES
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'google_sheets_connected': gs_manager is not None,
        'cache_size': len(CACHE),
        'integration_type': 'Direct Google Sheets API (Multiple Sheets Supported)'
    })

@app.route('/api/abacus-status', methods=['GET'])
def abacus_status():
    """System status endpoint - now shows Direct Google Sheets integration"""
    return jsonify({
        'platform': 'Expo Convention Contractors',
        'status': 'connected',
        'database': 'Direct Google Sheets API Integration',
        'multiple_sheets_support': True,
        'last_sync': datetime.now().isoformat(),
        'version': '4.0.0 - Direct Sheets',
        'cache_enabled': True,
        'cache_duration_seconds': CACHE_DURATION
    })

@app.route('/api/exhibitors', methods=['GET'])
def get_exhibitors():
    """Get list of all exhibitors with smart caching - SUPPORTS MULTIPLE SHEETS"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    
    try:
        exhibitors = load_exhibitors_from_sheets(force_refresh=force_refresh)
        return jsonify(exhibitors)
        
    except Exception as e:
        logger.error(f"Error getting exhibitors: {e}")
        return jsonify([]), 500

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """Get all orders with smart caching - SUPPORTS MULTIPLE SHEETS"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    orders = load_orders_from_sheets(force_refresh=force_refresh)
    return jsonify(orders)

@app.route('/api/orders/exhibitor/<exhibitor_name>', methods=['GET'])
def get_orders_by_exhibitor(exhibitor_name):
    """Get orders for a specific exhibitor with smart caching - SUPPORTS MULTIPLE SHEETS"""
    cache_key = f"exhibitor_{exhibitor_name}"
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    
    # Try cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return jsonify(cached_data)
    
    try:
        if not gs_manager:
            # Fallback to loading all orders and filtering
            all_orders = load_orders_from_sheets(force_refresh=force_refresh)
            exhibitor_orders = [
                order for order in all_orders 
                if order['exhibitor_name'].lower() == exhibitor_name.lower()
            ]
        else:
            # Use direct method for better performance - SUPPORTS MULTIPLE SHEETS
            exhibitor_orders = gs_manager.get_orders_for_exhibitor(SHEET_ID, exhibitor_name)
        
        delivered_count = len([o for o in exhibitor_orders if o['status'] == 'delivered'])
        
        result = {
            'exhibitor': exhibitor_name,
            'orders': exhibitor_orders,
            'total_orders': len(exhibitor_orders),
            'delivered_orders': delivered_count,
            'last_updated': datetime.now().isoformat(),
            'force_refreshed': force_refresh,
            'multiple_sheets_scanned': True
        }
        
        set_cache(cache_key, result)
        
        if force_refresh:
            logger.info(f"🔄 MANUAL REFRESH: Fresh data for {exhibitor_name} from multiple sheets")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting orders for exhibitor {exhibitor_name}: {e}")
        return jsonify({
            'exhibitor': exhibitor_name,
            'orders': [],
            'total_orders': 0,
            'delivered_orders': 0,
            'last_updated': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/orders/booth/<booth_number>', methods=['GET'])
def get_orders_by_booth(booth_number):
    """Get orders for a specific booth - SUPPORTS MULTIPLE SHEETS"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    orders = load_orders_from_sheets(force_refresh=force_refresh)
    booth_orders = [order for order in orders if order['booth_number'] == booth_number]
    
    return jsonify({
        'booth': booth_number,
        'orders': booth_orders,
        'total_orders': len(booth_orders),
        'last_updated': datetime.now().isoformat(),
        'multiple_sheets_scanned': True
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics - SUPPORTS MULTIPLE SHEETS"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    orders = load_orders_from_sheets(force_refresh=force_refresh)
    
    stats = {
        'total_orders': len(orders),
        'delivered': len([o for o in orders if o['status'] == 'delivered']),
        'in_process': len([o for o in orders if o['status'] == 'in-process']),
        'in_route': len([o for o in orders if o['status'] == 'in-route']),
        'out_for_delivery': len([o for o in orders if o['status'] == 'out-for-delivery']),
        'cancelled': len([o for o in orders if o['status'] == 'cancelled']),
        'last_updated': datetime.now().isoformat(),
        'multiple_sheets_scanned': True
    }
    
    return jsonify(stats)

@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """Get inventory data from Google Sheets"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    cache_key = "inventory"
    
    # Try cache first (unless force refresh)
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return jsonify(cached_data)
    
    try:
        if not gs_manager:
            return jsonify([])
        
        inventory = gs_manager.get_inventory(SHEET_ID)
        set_cache(cache_key, inventory)
        
        return jsonify(inventory)
        
    except Exception as e:
        logger.error(f"Error getting inventory: {e}")
        return jsonify([]), 500

@app.route('/api/worksheets', methods=['GET'])
def get_worksheets():
    """Get list of all worksheets in the Google Sheet"""
    try:
        if not gs_manager:
            return jsonify([])
        
        worksheets = gs_manager.get_worksheets(SHEET_ID)
        
        return jsonify({
            'worksheets': worksheets,
            'sections': [ws for ws in worksheets if ws.startswith('Section')],
            'total_count': len(worksheets)
        })
        
    except Exception as e:
        logger.error(f"Error getting worksheets: {e}")
        return jsonify({'worksheets': [], 'sections': [], 'total_count': 0}), 500

# NEW WRITE OPERATIONS (like your Streamlit app)
@app.route('/api/orders', methods=['POST'])
def add_order():
    """Add a new order to Google Sheets"""
    try:
        if not gs_manager:
            return jsonify({'error': 'Google Sheets not available'}), 500
        
        order_data = request.json
        
        # Validate required fields
        required_fields = ['Booth #', 'Exhibitor Name', 'Item']
        for field in required_fields:
            if not order_data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Add current timestamp and user
        order_data['User'] = order_data.get('User', 'API')
        
        # Add to main Orders sheet
        success = gs_manager.add_order(SHEET_ID, "Orders", order_data)
        
        if success:
            # Clear cache to force refresh
            if "all_orders" in CACHE:
                del CACHE["all_orders"]
            if "exhibitors" in CACHE:
                del CACHE["exhibitors"]
            
            return jsonify({'message': 'Order added successfully'}), 201
        else:
            return jsonify({'error': 'Failed to add order'}), 500
            
    except Exception as e:
        logger.error(f"Error adding order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<booth_number>/<item>/<color>', methods=['PUT'])
def update_order_status(booth_number, item, color):
    """Update order status in Google Sheets"""
    try:
        if not gs_manager:
            return jsonify({'error': 'Google Sheets not available'}), 500
        
        data = request.json
        new_status = data.get('status')
        user = data.get('user', 'API')
        worksheet = data.get('worksheet', 'Orders')
        
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        # Update the order
        success = gs_manager.update_order_status(
            SHEET_ID, worksheet, booth_number, item, color, new_status, user
        )
        
        if success:
            # Clear cache to force refresh
            if "all_orders" in CACHE:
                del CACHE["all_orders"]
            if f"exhibitor_{booth_number}" in CACHE:
                del CACHE[f"exhibitor_{booth_number}"]
            
            return jsonify({'message': 'Order status updated successfully'})
        else:
            return jsonify({'error': 'Failed to update order status'}), 500
            
    except Exception as e:
        logger.error(f"Error updating order status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/orders/<booth_number>/<item>/<color>', methods=['DELETE'])
def delete_order(booth_number, item, color):
    """Delete an order from Google Sheets"""
    try:
        if not gs_manager:
            return jsonify({'error': 'Google Sheets not available'}), 500
        
        # Get section from query params if provided
        section = request.args.get('section', '')
        
        # Delete the order
        success = gs_manager.delete_order(SHEET_ID, booth_number, item, color, section)
        
        if success:
            # Clear cache to force refresh
            if "all_orders" in CACHE:
                del CACHE["all_orders"]
            if "exhibitors" in CACHE:
                del CACHE["exhibitors"]
            
            return jsonify({'message': 'Order deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete order'}), 500
            
    except Exception as e:
        logger.error(f"Error deleting order: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all cached data - useful for forcing fresh data"""
    global CACHE
    CACHE = {}
    logger.info("🗑️ Cache cleared manually")
    return jsonify({'message': 'Cache cleared successfully'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

@app.route('/api/debug', methods=['GET'])
def debug_sheets():
    return jsonify({
        'sheet_id_being_used': SHEET_ID,
        'gs_manager_initialized': gs_manager is not None,
        'credentials_path': credentials_path
    })
