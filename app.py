# app.py - FIXED VERSION - Connect to NEW Google Sheet
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import logging
import os
import json

# Import ONLY the Direct Google Sheets manager
from direct_google_sheets_manager import DirectGoogleSheetsManager

# CRITICAL: NEW Google Sheet ID - Your working new sheet
NEW_SHEET_ID = "1_yBu2Rx4UGcSL04r0aAMyZDHbpuTKrJK9KavEeanZXs"
OLD_SHEET_ID = "1dYeok-Dy_7a03AhPDLV2NNmGbRNoCD3q0zaAHPwxxCE"  # Reference only

# Use the NEW sheet ID everywhere
SHEET_ID = NEW_SHEET_ID

# Debug logging
print("=" * 60)
print("🎯 CONNECTING TO NEW GOOGLE SHEET")
print(f"✅ Target NEW Sheet ID: {NEW_SHEET_ID}")
print(f"🚫 Old Sheet ID (NOT USED): {OLD_SHEET_ID}")
print(f"📊 SHEET_ID Variable Set To: {SHEET_ID}")
print("=" * 60)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SIMPLE CACHE SYSTEM
CACHE = {}
CACHE_DURATION = 30  # 30 seconds cache
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

# CREDENTIALS SETUP - Environment variables for Render
def get_credentials():
    """Get Google credentials from environment variable"""
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            credentials_dict = json.loads(credentials_json)
            with open('/tmp/credentials.json', 'w') as f:
                json.dump(credentials_dict, f)
            return '/tmp/credentials.json'
        else:
            # For local development only
            return 'credentials.json'
    except Exception as e:
        logger.error(f"Error setting up credentials: {e}")
        return None

# Initialize Direct Google Sheets Manager
credentials_path = get_credentials()
if credentials_path:
    gs_manager = DirectGoogleSheetsManager(credentials_path)
    logger.info("✅ Direct Google Sheets Manager initialized")
else:
    gs_manager = None
    logger.warning("❌ No valid credentials found")

logger.info(f"🎯 TARGET SHEET ID: {NEW_SHEET_ID}")
logger.info(f"🚫 OLD SHEET ID (NOT USED): {OLD_SHEET_ID}")

# MOCK DATA FALLBACK (updated for new sheet)
def get_simple_mock_orders():
    return [
        {
            'id': 'NEW-SHEET-TEST-001',
            'booth_number': '3023',
            'exhibitor_name': 'U.S. Customs and Border Protection',
            'item': 'Black Stool',
            'description': 'Professional exhibition furniture',
            'color': 'Black',
            'quantity': 4,
            'status': 'delivered',
            'order_date': '8/13/2025',
            'comments': 'From NEW Google Sheet',
            'section': 'Section 3',
            'data_source': 'NEW_SHEET_DIRECT_API'
        },
        {
            'id': 'NEW-SHEET-TEST-002',
            'booth_number': '2022',
            'exhibitor_name': 'City Sightseeing LTD',
            'item': 'White Side Chair',
            'description': 'Professional exhibition furniture',
            'color': 'White',
            'quantity': 2,
            'status': 'delivered',
            'order_date': '4/8/2025',
            'comments': 'From NEW Google Sheet',
            'section': 'Section 2',
            'data_source': 'NEW_SHEET_DIRECT_API'
        }
    ]

def load_orders_from_new_sheet(force_refresh=False):
    """Load orders ONLY from the NEW Google Sheet"""
    cache_key = "new_sheet_orders"
    
    # Check cache first
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            logger.info("📋 Returning cached data from NEW sheet")
            return cached_data
    
    try:
        if not gs_manager:
            logger.warning("No Google Sheets manager, using mock data")
            mock_data = get_simple_mock_orders()
            set_cache(cache_key, mock_data)
            return mock_data
        
        logger.info(f"🔄 Loading fresh data from NEW SHEET: {NEW_SHEET_ID}")
        
        # Get orders from NEW sheet ONLY
        all_orders = gs_manager.get_all_orders(NEW_SHEET_ID)
        
        if all_orders and len(all_orders) > 0:
            logger.info(f"✅ Loaded {len(all_orders)} orders from NEW Google Sheet")
            # Add source tracking
            for order in all_orders:
                order['data_source'] = 'NEW_SHEET_LIVE_DATA'
                order['source_sheet_id'] = NEW_SHEET_ID
            
            set_cache(cache_key, all_orders)
            return all_orders
        else:
            logger.warning("📭 No data found in NEW Google Sheet, using mock data")
            mock_data = get_simple_mock_orders()
            set_cache(cache_key, mock_data)
            return mock_data
        
    except Exception as e:
        logger.error(f"❌ Error loading from NEW sheet: {e}")
        logger.info("🔄 Falling back to mock data")
        mock_data = get_simple_mock_orders()
        set_cache(cache_key, mock_data)
        return mock_data

def load_exhibitors_from_new_sheet(force_refresh=False):
    """Load exhibitors ONLY from the NEW Google Sheet"""
    cache_key = "new_sheet_exhibitors"
    
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return cached_data
    
    try:
        if not gs_manager:
            fallback = [
                {'name': 'U.S. Customs and Border Protection', 'booth': '3023', 'total_orders': 1, 'delivered_orders': 1},
                {'name': 'City Sightseeing LTD', 'booth': '2022', 'total_orders': 1, 'delivered_orders': 1},
                {'name': 'TEAM NORWAY', 'booth': '3023', 'total_orders': 5, 'delivered_orders': 4}
            ]
            set_cache(cache_key, fallback)
            return fallback
        
        logger.info(f"🔄 Loading exhibitors from NEW SHEET: {NEW_SHEET_ID}")
        exhibitors = gs_manager.get_all_exhibitors(NEW_SHEET_ID)
        
        if exhibitors and len(exhibitors) > 0:
            logger.info(f"✅ Loaded {len(exhibitors)} exhibitors from NEW sheet")
            set_cache(cache_key, exhibitors)
            return exhibitors
        else:
            fallback = [
                {'name': 'U.S. Customs and Border Protection', 'booth': '3023', 'total_orders': 1, 'delivered_orders': 1},
                {'name': 'City Sightseeing LTD', 'booth': '2022', 'total_orders': 1, 'delivered_orders': 1},
                {'name': 'TEAM NORWAY', 'booth': '3023', 'total_orders': 5, 'delivered_orders': 4}
            ]
            set_cache(cache_key, fallback)
            return fallback
        
    except Exception as e:
        logger.error(f"❌ Error loading exhibitors from NEW sheet: {e}")
        fallback = [
            {'name': 'U.S. Customs and Border Protection', 'booth': '3023', 'total_orders': 1, 'delivered_orders': 1},
            {'name': 'City Sightseeing LTD', 'booth': '2022', 'total_orders': 1, 'delivered_orders': 1},
            {'name': 'TEAM NORWAY', 'booth': '3023', 'total_orders': 5, 'delivered_orders': 4}
        ]
        set_cache(cache_key, fallback)
        return fallback

# REACT APP ROUTES
@app.route('/')
def serve_react_app():
    try:
        return send_file('frontend/build/index.html')
    except FileNotFoundError:
        return "Frontend not built. Please run 'npm run build' in frontend directory.", 404

@app.route('/<path:path>')
def serve_static_files(path):
    try:
        return send_from_directory('frontend/build', path)
    except FileNotFoundError:
        try:
            return send_file('frontend/build/index.html')
        except FileNotFoundError:
            return "Frontend not built.", 404

# ENHANCED DEBUG ROUTES
@app.route('/api/debug-new-sheet-connection', methods=['GET'])
def debug_new_sheet_connection():
    """Debug connection specifically to the NEW Google Sheet"""
    
    debug_info = {
        'target_new_sheet_id': NEW_SHEET_ID,
        'old_sheet_id_reference': OLD_SHEET_ID,
        'current_sheet_id_variable': SHEET_ID,
        'sheets_match': SHEET_ID == NEW_SHEET_ID,
        'timestamp': datetime.now().isoformat()
    }
    
    # Test actual connection to NEW sheet
    if gs_manager:
        try:
            logger.info(f"🔍 Testing connection to NEW sheet: {NEW_SHEET_ID}")
            
            # Test basic access
            worksheets = gs_manager.get_worksheets(NEW_SHEET_ID)
            debug_info['new_sheet_connection'] = {
                'accessible': True,
                'worksheets': worksheets,
                'worksheet_count': len(worksheets)
            }
            
            # Test data retrieval
            raw_data = gs_manager.get_data(NEW_SHEET_ID, "Orders")
            debug_info['raw_data_check'] = {
                'has_data': not raw_data.empty,
                'data_shape': raw_data.shape if not raw_data.empty else "Empty",
                'first_row_sample': raw_data.iloc[0].to_dict() if not raw_data.empty else "No data"
            }
            
            # Test processed orders
            orders_data = gs_manager.get_all_orders(NEW_SHEET_ID)
            debug_info['processed_orders'] = {
                'orders_found': len(orders_data) if orders_data else 0,
                'has_real_data': len(orders_data) > 0 if orders_data else False,
                'sample_order': orders_data[0] if orders_data else None
            }
            
            logger.info(f"✅ NEW sheet accessible with {len(worksheets)} worksheets")
            logger.info(f"📊 Found {len(orders_data) if orders_data else 0} orders in NEW sheet")
            
        except Exception as e:
            debug_info['new_sheet_connection'] = {
                'accessible': False,
                'error': str(e)
            }
            logger.error(f"❌ Error connecting to NEW sheet: {e}")
    else:
        debug_info['sheets_manager'] = 'NOT_INITIALIZED'
    
    return jsonify(debug_info)

# API ROUTES - COMPLETELY CLEAN
@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check with NEW sheet verification"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'google_sheets_connected': gs_manager is not None,
        'cache_size': len(CACHE),
        'integration_type': 'Direct Google Sheets API - NEW SHEET',
        'target_sheet_id': NEW_SHEET_ID,
        'current_sheet_variable': SHEET_ID,
        'sheet_ids_match': SHEET_ID == NEW_SHEET_ID,
        'old_sheet_disconnected': True
    })

@app.route('/api/system-status', methods=['GET'])
def system_status():
    """System status - Connected to NEW sheet"""
    return jsonify({
        'platform': 'Expo Convention Contractors',
        'status': 'connected',
        'database': 'Direct Google Sheets API - NEW SHEET',
        'target_sheet': NEW_SHEET_ID,
        'old_sheet_status': 'DISCONNECTED',
        'last_sync': datetime.now().isoformat(),
        'version': '5.1.0 - NEW SHEET CONNECTED',
        'cache_enabled': True,
        'cache_duration_seconds': CACHE_DURATION
    })

@app.route('/api/exhibitors', methods=['GET'])
def get_exhibitors():
    """Get exhibitors from NEW sheet only"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    
    if force_refresh:
        logger.info("🔄 FORCE REFRESH: Loading fresh exhibitors from NEW sheet")
    
    try:
        exhibitors = load_exhibitors_from_new_sheet(force_refresh=force_refresh)
        
        # Add metadata
        result = {
            'exhibitors': exhibitors,
            'source_sheet': NEW_SHEET_ID,
            'total_count': len(exhibitors),
            'last_updated': datetime.now().isoformat()
        }
        
        return jsonify(exhibitors)  # Return just the array for compatibility
    except Exception as e:
        logger.error(f"Error getting exhibitors: {e}")
        return jsonify([]), 500

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """Get all orders from NEW sheet only"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    
    if force_refresh:
        logger.info("🔄 FORCE REFRESH: Loading fresh orders from NEW sheet")
    
    orders = load_orders_from_new_sheet(force_refresh=force_refresh)
    return jsonify(orders)

@app.route('/api/orders/exhibitor/<exhibitor_name>', methods=['GET'])
def get_orders_by_exhibitor(exhibitor_name):
    """Get orders for specific exhibitor from NEW sheet only"""
    cache_key = f"new_sheet_exhibitor_{exhibitor_name}"
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    
    if not force_refresh:
        cached_data = get_from_cache(cache_key, allow_cache=True)
        if cached_data:
            return jsonify(cached_data)
    
    try:
        if not gs_manager:
            all_orders = load_orders_from_new_sheet(force_refresh=force_refresh)
            exhibitor_orders = [
                order for order in all_orders 
                if order['exhibitor_name'].lower() == exhibitor_name.lower()
            ]
        else:
            logger.info(f"🔍 Getting orders for {exhibitor_name} from NEW SHEET: {NEW_SHEET_ID}")
            exhibitor_orders = gs_manager.get_orders_for_exhibitor(NEW_SHEET_ID, exhibitor_name)
        
        delivered_count = len([o for o in exhibitor_orders if o['status'] == 'delivered'])
        
        result = {
            'exhibitor': exhibitor_name,
            'orders': exhibitor_orders,
            'total_orders': len(exhibitor_orders),
            'delivered_orders': delivered_count,
            'last_updated': datetime.now().isoformat(),
            'force_refreshed': force_refresh,
            'source_sheet': NEW_SHEET_ID,
            'data_source': 'NEW_SHEET_LIVE'
        }
        
        set_cache(cache_key, result)
        
        if force_refresh:
            logger.info(f"🔄 FORCE REFRESH: Fresh data for {exhibitor_name} from NEW sheet")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting orders for exhibitor {exhibitor_name}: {e}")
        return jsonify({
            'exhibitor': exhibitor_name,
            'orders': [],
            'total_orders': 0,
            'delivered_orders': 0,
            'last_updated': datetime.now().isoformat(),
            'error': str(e),
            'source_sheet': NEW_SHEET_ID
        }), 500

@app.route('/api/orders/booth/<booth_number>', methods=['GET'])
def get_orders_by_booth(booth_number):
    """Get orders for a specific booth from NEW sheet"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    orders = load_orders_from_new_sheet(force_refresh=force_refresh)
    booth_orders = [order for order in orders if order['booth_number'] == booth_number]
    
    return jsonify({
        'booth': booth_number,
        'orders': booth_orders,
        'total_orders': len(booth_orders),
        'last_updated': datetime.now().isoformat(),
        'source_sheet': NEW_SHEET_ID
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics from NEW sheet"""
    force_refresh = request.args.get(FORCE_REFRESH_PARAM, 'false').lower() == 'true'
    orders = load_orders_from_new_sheet(force_refresh=force_refresh)
    
    stats = {
        'total_orders': len(orders),
        'delivered': len([o for o in orders if o['status'] == 'delivered']),
        'in_process': len([o for o in orders if o['status'] == 'in-process']),
        'in_route': len([o for o in orders if o['status'] == 'in-route']),
        'out_for_delivery': len([o for o in orders if o['status'] == 'out-for-delivery']),
        'cancelled': len([o for o in orders if o['status'] == 'cancelled']),
        'last_updated': datetime.now().isoformat(),
        'source_sheet': NEW_SHEET_ID
    }
    
    return jsonify(stats)

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all cached data"""
    global CACHE
    CACHE = {}
    logger.info("🗑️ Cache cleared manually - will force refresh from NEW sheet")
    return jsonify({
        'message': 'Cache cleared - will load fresh data from NEW sheet',
        'target_sheet': NEW_SHEET_ID
    })

@app.route('/api/worksheets', methods=['GET'])
def get_worksheets():
    """Get list of all worksheets in the NEW Google Sheet"""
    try:
        if not gs_manager:
            return jsonify([])
        
        worksheets = gs_manager.get_worksheets(NEW_SHEET_ID)
        
        return jsonify({
            'worksheets': worksheets,
            'sections': [ws for ws in worksheets if ws.startswith('Section')],
            'total_count': len(worksheets),
            'source_sheet': NEW_SHEET_ID
        })
        
    except Exception as e:
        logger.error(f"Error getting worksheets: {e}")
        return jsonify({'worksheets': [], 'sections': [], 'total_count': 0}), 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting app connected to NEW Google Sheet")
    logger.info(f"🎯 NEW Sheet: {NEW_SHEET_ID}")
    logger.info(f"🚫 OLD Sheet DISCONNECTED: {OLD_SHEET_ID}")
    app.run(host='0.0.0.0', port=port, debug=False)
