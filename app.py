# app.py - COMPLETELY CLEAN VERSION - NO ABACUS AI
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import time
import logging
import os
import json

# Import ONLY the Direct Google Sheets manager
from direct_google_sheets_manager import DirectGoogleSheetsManager

# CRITICAL: Debug which sheet we're targeting
NEW_SHEET_ID = "1_yBu2Rx4UGcSL04r0aAMyZDHbpuTKrJK9KavEeanZXs"
OLD_SHEET_ID = "1dYeok-Dy_7a03AhPDLV2NNmGbRNoCD3q0zaAHPwxxCE"

# Use the NEW sheet ID everywhere
SHEET_ID = NEW_SHEET_ID

# Debug logging
print("=" * 50)
print("🎯 SHEET CONNECTION DEBUG")
print(f"✅ Target NEW Sheet ID: {NEW_SHEET_ID}")
print(f"🚫 Old Sheet ID (NOT USED): {OLD_SHEET_ID}")
print(f"📊 SHEET_ID Variable Set To: {SHEET_ID}")
print("=" * 50)

# Initialize Flask app FIRST
app = Flask(__name__, static_folder='frontend/build', static_url_path='')
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SIMPLE CACHE SYSTEM (NO ABACUS)
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

# CREDENTIALS SETUP
def get_credentials():
    """Get Google credentials from environment variable or file"""
    try:
        credentials_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        if credentials_json:
            credentials_dict = json.loads(credentials_json)
            with open('/tmp/credentials.json', 'w') as f:
                json.dump(credentials_dict, f)
            return '/tmp/credentials.json'
        else:
            return 'credentials.json'  # Local file for development
    except Exception as e:
        logger.error(f"Error setting up credentials: {e}")
        return None

# Initialize Direct Google Sheets Manager ONLY
credentials_path = get_credentials()
if credentials_path:
    gs_manager = DirectGoogleSheetsManager(credentials_path)
    logger.info("✅ Direct Google Sheets Manager initialized")
else:
    gs_manager = None
    logger.warning("❌ No valid credentials found")

logger.info(f"🎯 TARGET SHEET ID: {NEW_SHEET_ID}")
logger.info(f"🚫 OLD SHEET ID (NOT USED): {OLD_SHEET_ID}")

# MOCK DATA FALLBACK (simplified)
def get_simple_mock_orders():
    return [
        {
            'id': 'NEW-SHEET-001',
            'booth_number': 'N-001',
            'exhibitor_name': 'New Sheet Test Company',
            'item': 'Test Item from New Sheet',
            'description': 'This data comes from the NEW Google Sheet',
            'color': 'Blue',
            'quantity': 1,
            'status': 'in-process',
            'order_date': datetime.now().strftime('%Y-%m-%d'),
            'comments': 'Connected to NEW Google Sheet',
            'section': 'New Section',
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
            fallback = [{'name': 'Test Company (New Sheet)', 'booth': 'N-001', 'total_orders': 1, 'delivered_orders': 0}]
            set_cache(cache_key, fallback)
            return fallback
        
        logger.info(f"🔄 Loading exhibitors from NEW SHEET: {NEW_SHEET_ID}")
        exhibitors = gs_manager.get_all_exhibitors(NEW_SHEET_ID)
        
        if exhibitors and len(exhibitors) > 0:
            logger.info(f"✅ Loaded {len(exhibitors)} exhibitors from NEW sheet")
            set_cache(cache_key, exhibitors)
            return exhibitors
        else:
            fallback = [{'name': 'Test Company (New Sheet)', 'booth': 'N-001', 'total_orders': 1, 'delivered_orders': 0}]
            set_cache(cache_key, fallback)
            return fallback
        
    except Exception as e:
        logger.error(f"❌ Error loading exhibitors from NEW sheet: {e}")
        fallback = [{'name': 'Test Company (New Sheet)', 'booth': 'N-001', 'total_orders': 1, 'delivered_orders': 0}]
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

# DEBUG ROUTES - NOW IN CORRECT LOCATION (after app is defined)
@app.route('/api/debug-sheet-connection', methods=['GET'])
def debug_sheet_connection():
    """Debug which sheet we're actually connecting to"""
    
    debug_info = {
        'target_new_sheet_id': NEW_SHEET_ID,
        'old_sheet_id_reference': OLD_SHEET_ID,
        'current_sheet_id_variable': SHEET_ID,
        'sheets_match': SHEET_ID == NEW_SHEET_ID,
        'environment_check': {
            'google_credentials_exist': bool(os.environ.get('GOOGLE_CREDENTIALS_JSON')),
            'port': os.environ.get('PORT', 'default'),
        }
    }
    
    # Test actual connection to NEW sheet
    if gs_manager:
        try:
            print(f"🔍 Testing connection to NEW sheet: {NEW_SHEET_ID}")
            worksheets = gs_manager.get_worksheets(NEW_SHEET_ID)
            debug_info['new_sheet_connection'] = {
                'accessible': True,
                'worksheets': worksheets,
                'worksheet_count': len(worksheets)
            }
            
            # Try to get actual data
            orders_data = gs_manager.get_all_orders(NEW_SHEET_ID)
            debug_info['new_sheet_data'] = {
                'orders_found': len(orders_data) if orders_data else 0,
                'has_real_data': len(orders_data) > 0 if orders_data else False
            }
            
            print(f"✅ NEW sheet accessible with {len(worksheets)} worksheets")
            print(f"📊 Found {len(orders_data) if orders_data else 0} orders in NEW sheet")
            
        except Exception as e:
            debug_info['new_sheet_connection'] = {
                'accessible': False,
                'error': str(e)
            }
            print(f"❌ Error connecting to NEW sheet: {e}")
    else:
        debug_info['sheets_manager'] = 'NOT_INITIALIZED'
    
    return jsonify(debug_info)

# API ROUTES - COMPLETELY CLEAN
@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check with sheet verification"""
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'google_sheets_connected': gs_manager is not None,
        'cache_size': len(CACHE),
        'integration_type': 'Direct Google Sheets API (NO ABACUS)',
        'target_sheet_id': NEW_SHEET_ID,  # Show which sheet we're targeting
        'current_sheet_variable': SHEET_ID,
        'sheet_ids_match': SHEET_ID == NEW_SHEET_ID,
        'abacus_ai_status': 'COMPLETELY_DISCONNECTED'
    })

@app.route('/api/system-status', methods=['GET'])  # RENAMED FROM abacus-status
def system_status():
    """System status - NO ABACUS REFERENCES"""
    return jsonify({
        'platform': 'Expo Convention Contractors',
        'status': 'connected',
        'database': 'Pure Direct Google Sheets API',
        'abacus_ai': 'DISCONNECTED',
        'target_sheet': NEW_SHEET_ID,
        'last_sync': datetime.now().isoformat(),
        'version': '5.0.0 - PURE DIRECT SHEETS',
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
        return jsonify(exhibitors)
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
            'abacus_status': 'DISCONNECTED'
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

@app.route('/api/clear-cache', methods=['POST'])
def clear_cache():
    """Clear all cached data"""
    global CACHE
    CACHE = {}
    logger.info("🗑️ Cache cleared manually - will force refresh from NEW sheet")
    return jsonify({'message': 'Cache cleared - will load fresh data from NEW sheet'})

@app.route('/api/debug-connection', methods=['GET'])
def debug_connection():
    """Debug the Google Sheets connection"""
    try:
        debug_info = {
            'target_sheet_id': NEW_SHEET_ID,
            'old_sheet_id_reference': OLD_SHEET_ID,
            'gs_manager_exists': gs_manager is not None,
            'credentials_path': credentials_path,
            'abacus_ai_status': 'COMPLETELY DISCONNECTED'
        }
        
        if gs_manager:
            # Test connection to NEW sheet
            try:
                worksheets = gs_manager.get_worksheets(NEW_SHEET_ID)
                debug_info['new_sheet_worksheets'] = worksheets
                debug_info['new_sheet_accessible'] = True
                
                # Try to get sample data
                raw_data = gs_manager.get_data(NEW_SHEET_ID, "Orders")
                debug_info['new_sheet_has_data'] = not raw_data.empty
                debug_info['new_sheet_data_shape'] = raw_data.shape if not raw_data.empty else "Empty"
                debug_info['new_sheet_sample'] = raw_data.head(2).to_dict() if not raw_data.empty else "No data"
                
            except Exception as e:
                debug_info['new_sheet_error'] = str(e)
                debug_info['new_sheet_accessible'] = False
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'target_sheet_id': NEW_SHEET_ID,
            'abacus_status': 'DISCONNECTED'
        })


# Add these routes to your app.py (after the other routes)

@app.route('/api/test-new-sheet-raw', methods=['GET'])
def test_new_sheet_raw():
    """Test the raw data structure of the NEW Google Sheet"""
    try:
        if not gs_manager:
            return jsonify({'error': 'No Google Sheets manager'}), 500
        
        logger.info(f"🔍 Testing raw data from NEW sheet: {NEW_SHEET_ID}")
        
        # Get raw data from NEW sheet
        raw_data = gs_manager.get_data(NEW_SHEET_ID, "Orders")
        
        debug_info = {
            'sheet_id': NEW_SHEET_ID,
            'worksheet_name': 'Orders',
            'data_shape': raw_data.shape if not raw_data.empty else "Empty",
            'is_empty': raw_data.empty,
            'columns_found': raw_data.columns.tolist() if not raw_data.empty else [],
            'first_few_rows': raw_data.head(3).to_dict() if not raw_data.empty else "No data",
            'total_rows': len(raw_data) if not raw_data.empty else 0
        }
        
        # If we have data, show headers and first row
        if not raw_data.empty and len(raw_data) > 0:
            debug_info['first_row_values'] = raw_data.iloc[0].to_dict()
            debug_info['headers_in_first_row'] = raw_data.iloc[0].tolist()
            
            # Show actual data (not just headers)
            if len(raw_data) > 1:
                debug_info['second_row_values'] = raw_data.iloc[1].to_dict()
        
        logger.info(f"📊 Raw data test complete: {len(raw_data) if not raw_data.empty else 0} rows")
        return jsonify(debug_info)
        
    except Exception as e:
        logger.error(f"❌ Error testing raw data: {e}")
        return jsonify({
            'error': str(e),
            'sheet_id': NEW_SHEET_ID,
            'worksheet': 'Orders'
        }), 500

@app.route('/api/force-process-new-sheet', methods=['GET'])
def force_process_new_sheet():
    """Force process data from NEW sheet with detailed logging"""
    try:
        if not gs_manager:
            return jsonify({'error': 'No Google Sheets manager'}), 500
        
        logger.info(f"🔄 FORCE PROCESSING NEW SHEET: {NEW_SHEET_ID}")
        
        # Get raw data
        raw_data = gs_manager.get_data(NEW_SHEET_ID, "Orders")
        logger.info(f"📊 Raw data shape: {raw_data.shape}")
        
        if raw_data.empty:
            return jsonify({
                'status': 'empty_sheet',
                'message': 'NEW Google Sheet is empty - please add data',
                'sheet_id': NEW_SHEET_ID
            })
        
        # Process the data
        processed_orders = gs_manager.process_orders_dataframe(raw_data)
        logger.info(f"✅ Processed {len(processed_orders)} orders from NEW sheet")
        
        return jsonify({
            'status': 'success',
            'sheet_id': NEW_SHEET_ID,
            'raw_rows': len(raw_data),
            'processed_orders': len(processed_orders),
            'sample_order': processed_orders[0] if processed_orders else None,
            'all_orders': processed_orders[:3]  # Show first 3 orders
        })
        
    except Exception as e:
        logger.error(f"❌ Error processing NEW sheet: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'sheet_id': NEW_SHEET_ID
        }), 500

@app.route('/api/clear-cache-and-refresh', methods=['GET'])
def clear_cache_and_refresh():
    """Clear cache and immediately return fresh data"""
    try:
        # Clear cache
        global CACHE
        CACHE = {}
        logger.info("🗑️ Cache cleared")
        
        # Get fresh data
        fresh_orders = load_orders_from_new_sheet(force_refresh=True)
        fresh_exhibitors = load_exhibitors_from_new_sheet(force_refresh=True)
        
        return jsonify({
            'status': 'success',
            'cache_cleared': True,
            'fresh_orders_count': len(fresh_orders),
            'fresh_exhibitors_count': len(fresh_exhibitors),
            'sample_orders': fresh_orders[:2] if fresh_orders else [],
            'sample_exhibitors': fresh_exhibitors[:3] if fresh_exhibitors else [],
            'source_sheet': NEW_SHEET_ID
        })
        
    except Exception as e:
        logger.error(f"❌ Error clearing cache and refreshing: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting PURE Direct Google Sheets app on port {port}")
    logger.info(f"🎯 Connected to NEW sheet: {NEW_SHEET_ID}")
    logger.info(f"🚫 OLD sheet DISCONNECTED: {OLD_SHEET_ID}")
    app.run(host='0.0.0.0', port=port, debug=False)
