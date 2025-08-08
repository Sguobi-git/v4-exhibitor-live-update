# direct_google_sheets_manager.py
# Adapted from your working Streamlit app - Direct Google Sheets API integration

import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DirectGoogleSheetsManager:
    """
    Direct Google Sheets Manager - adapted from your working Streamlit app
    No Abacus AI dependencies - pure Google Sheets API
    """
    
    def __init__(self, credentials_path: str = None):
        """
        Initialize Direct Google Sheets Manager
        
        Args:
            credentials_path: Path to your Google service account JSON file
        """
        self.credentials_path = credentials_path
        self.gc = None
        self.setup_client()
    
    def setup_client(self):
        """Setup Google Sheets client"""
        try:
            if self.credentials_path:
                # Use service account credentials
                credentials = Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=[
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                )
                self.gc = gspread.authorize(credentials)
            else:
                # Use default authentication (for development)
                self.gc = gspread.service_account()
            
            logger.info("Direct Google Sheets client initialized successfully")
            
        except Exception as e:
            logger.error(f"Error setting up Google Sheets client: {e}")
            self.gc = None
    
    def get_data(self, sheet_id: str, worksheet_name: str = "Orders") -> pd.DataFrame:
        """
        Get data from Google Sheets as DataFrame (like your Streamlit app)
        
        Args:
            sheet_id: Google Sheet ID
            worksheet_name: Name of the worksheet
            
        Returns:
            pandas DataFrame with the sheet data
        """
        try:
            if not self.gc:
                raise Exception("Google Sheets client not initialized")
            
            # Open the spreadsheet
            spreadsheet = self.gc.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(worksheet_name)
            
            # Get all values
            data = worksheet.get_all_values()
            
            if not data:
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            logger.info(f"Successfully loaded {len(df)} rows from {worksheet_name}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting data from sheet: {e}")
            return pd.DataFrame()
    
    def get_worksheets(self, sheet_id: str) -> List[str]:
        """
        Get list of worksheet names (like your Streamlit app)
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of worksheet names
        """
        try:
            if not self.gc:
                return []
            
            spreadsheet = self.gc.open_by_key(sheet_id)
            worksheets = [ws.title for ws in spreadsheet.worksheets()]
            
            logger.info(f"Found worksheets: {worksheets}")
            return worksheets
            
        except Exception as e:
            logger.error(f"Error getting worksheets: {e}")
            return []
    
    def process_orders_dataframe(self, df: pd.DataFrame) -> List[Dict]:
        """
        Process raw DataFrame and convert to order dictionaries (adapted from your app)
        
        Args:
            df: Raw DataFrame from Google Sheets
            
        Returns:
            List of order dictionaries for your React app
        """
        orders = []
        
        try:
            if df.empty or len(df) < 2:
                return []
            
            # Use first row as headers (like your Streamlit app)
            df.columns = df.iloc[0].str.strip()
            df = df[1:]  # Remove header row
            df = df.reset_index(drop=True)
            
            logger.info(f"Using headers: {df.columns.tolist()}")
            
            # Process each row
            for idx, row in df.iterrows():
                # Skip empty rows
                if row.isna().all():
                    continue
                
                # Extract order data (matching your Streamlit app structure)
                booth_num = str(row.get('Booth #', '')).strip()
                exhibitor_name = str(row.get('Exhibitor Name', '')).strip()
                item = str(row.get('Item', '')).strip()
                
                # Skip rows without essential data
                if not booth_num or not exhibitor_name:
                    continue
                
                # Create order ID
                date = str(row.get('Date', '')).strip()
                order_id = f"ORD-{date.replace('/', '-')}-{booth_num}-{idx}"
                
                # Build order dictionary (matching your React app format)
                order = {
                    'id': order_id,
                    'booth_number': booth_num,
                    'exhibitor_name': exhibitor_name,
                    'item': item,
                    'description': f"Order: {item}",
                    'color': str(row.get('Color', '')).strip(),
                    'quantity': self._safe_int(row.get('Quantity', '1')),
                    'status': self.map_order_status(str(row.get('Status', '')).strip()),
                    'order_date': date,
                    'comments': str(row.get('Comments', '')).strip(),
                    'section': str(row.get('Section', '')).strip(),
                    'type': str(row.get('Type', '')).strip(),
                    'user': str(row.get('User', '')).strip(),
                    'hour': str(row.get('Hour', '')).strip(),
                    'boomers_quantity': self._safe_int(row.get("Boomer's Quantity", '0')),
                    'direct_sheets_processed': True,
                    'data_source': 'Direct Google Sheets API'
                }
                
                orders.append(order)
            
            logger.info(f"Processed {len(orders)} valid orders from Google Sheets")
            return orders
            
        except Exception as e:
            logger.error(f"Error processing orders data: {e}")
            return []
    
    def map_order_status(self, sheet_status: str) -> str:
        """
        Map Google Sheets status to React app status format (from your Streamlit app)
        
        Args:
            sheet_status: Status from Google Sheets
            
        Returns:
            Mapped status for React app
        """
        status_mapping = {
            'Delivered': 'delivered',
            'Received': 'delivered',
            'Out for delivery': 'out-for-delivery',
            'In route from warehouse': 'in-route',
            'In Process': 'in-process',
            'cancelled': 'cancelled',
            'Cancelled': 'cancelled',
            'New': 'in-process'
        }
        
        return status_mapping.get(sheet_status, 'in-process')
    
    def _safe_int(self, value, default=1):
        """Safely convert value to int"""
        try:
            return int(float(str(value))) if value else default
        except (ValueError, TypeError):
            return default
    
    def get_all_orders(self, sheet_id: str) -> List[Dict]:
        """
        Get all orders from all sheets (main Orders + section sheets)
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of all orders from all sheets
        """
        try:
            all_orders = []
            
            # Get main Orders sheet
            main_df = self.get_data(sheet_id, "Orders")
            if not main_df.empty:
                main_orders = self.process_orders_dataframe(main_df)
                all_orders.extend(main_orders)
            
            # Get section sheets (like your Streamlit app)
            worksheets = self.get_worksheets(sheet_id)
            section_sheets = [ws for ws in worksheets if ws.startswith("Section")]
            
            for section in section_sheets:
                section_df = self.get_data(sheet_id, section)
                if not section_df.empty:
                    section_orders = self.process_orders_dataframe(section_df)
                    all_orders.extend(section_orders)
                    logger.info(f"Loaded {len(section_orders)} orders from {section}")
            
            logger.info(f"Total orders loaded: {len(all_orders)}")
            return all_orders
            
        except Exception as e:
            logger.error(f"Error getting all orders: {e}")
            return []
    
    def get_all_exhibitors(self, sheet_id: str) -> List[Dict]:
        """
        Get list of all exhibitors with their order counts
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of exhibitor dictionaries
        """
        try:
            all_orders = self.get_all_orders(sheet_id)
            
            if not all_orders:
                return []
            
            # Group by exhibitor (like your Streamlit app logic)
            exhibitors = {}
            for order in all_orders:
                name = order['exhibitor_name']
                booth = order['booth_number']
                
                if name not in exhibitors:
                    exhibitors[name] = {
                        'name': name,
                        'booth': booth,
                        'total_orders': 0,
                        'delivered_orders': 0
                    }
                
                exhibitors[name]['total_orders'] += 1
                if order['status'] == 'delivered':
                    exhibitors[name]['delivered_orders'] += 1
            
            return list(exhibitors.values())
            
        except Exception as e:
            logger.error(f"Error getting exhibitors: {e}")
            return []
    
    def get_orders_for_exhibitor(self, sheet_id: str, exhibitor_name: str) -> List[Dict]:
        """
        Get all orders for a specific exhibitor
        
        Args:
            sheet_id: Google Sheet ID
            exhibitor_name: Name of the exhibitor
            
        Returns:
            List of orders for the exhibitor
        """
        try:
            all_orders = self.get_all_orders(sheet_id)
            
            # Filter by exhibitor name (case-insensitive)
            exhibitor_orders = [
                order for order in all_orders 
                if order['exhibitor_name'].lower() == exhibitor_name.lower()
            ]
            
            logger.info(f"Found {len(exhibitor_orders)} orders for {exhibitor_name}")
            return exhibitor_orders
            
        except Exception as e:
            logger.error(f"Error getting orders for exhibitor {exhibitor_name}: {e}")
            return []
    
    def update_order_status(self, sheet_id: str, worksheet: str, booth_num: str, 
                           item_name: str, color: str, status: str, user: str) -> bool:
        """
        Update order status (adapted from your Streamlit app)
        
        Args:
            sheet_id: Google Sheet ID
            worksheet: Worksheet name
            booth_num: Booth number
            item_name: Item name
            color: Color
            status: New status
            user: User making the change
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.gc:
                return False
            
            # Open the spreadsheet and worksheet
            spreadsheet = self.gc.open_by_key(sheet_id)
            ws = spreadsheet.worksheet(worksheet)
            
            # Get all data
            data = ws.get_all_values()
            
            if not data:
                return False
            
            # Find the row to update
            headers = data[0]
            
            # Find column indices
            status_col = None
            user_col = None
            
            for i, header in enumerate(headers):
                if header.strip() == 'Status':
                    status_col = i
                elif header.strip() == 'User':
                    user_col = i
            
            if status_col is None:
                logger.error("Status column not found")
                return False
            
            # Find the row with matching booth, item, and color
            for i, row in enumerate(data[1:], start=2):  # Skip header, start from row 2
                if (len(row) > max(status_col, user_col or 0) and
                    str(row[0]).strip() == str(booth_num).strip() and  # Booth #
                    str(row[3]).strip() == str(item_name).strip() and  # Item
                    str(row[4]).strip() == str(color).strip()):  # Color
                    
                    # Update status
                    ws.update_cell(i, status_col + 1, status)
                    
                    # Update user if column exists
                    if user_col is not None:
                        ws.update_cell(i, user_col + 1, user)
                    
                    logger.info(f"Updated status for booth {booth_num}, item {item_name} to {status}")
                    return True
            
            logger.warning(f"Order not found: booth {booth_num}, item {item_name}, color {color}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False
    
    def add_order(self, sheet_id: str, worksheet: str, order_data: Dict) -> bool:
        """
        Add a new order to the sheet (adapted from your direct_add_order function)
        
        Args:
            sheet_id: Google Sheet ID
            worksheet: Worksheet name (usually "Orders")
            order_data: Dictionary containing order information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.gc:
                return False
            
            # Open the spreadsheet and worksheet
            spreadsheet = self.gc.open_by_key(sheet_id)
            ws = spreadsheet.worksheet(worksheet)
            
            # Get current date and time
            now = datetime.now()
            current_date = now.strftime("%m/%d/%Y")
            current_time = now.strftime("%I:%M:%S %p")
            
            # Prepare row data (matching your Streamlit app structure)
            row_data = [
                order_data.get('Booth #', ''),
                order_data.get('Section', ''),
                order_data.get('Exhibitor Name', ''),
                order_data.get('Item', ''),
                order_data.get('Color', ''),
                order_data.get('Quantity', 1),
                current_date,
                current_time,
                order_data.get('Status', 'In Process'),
                order_data.get('Type', 'New Order'),
                order_data.get('Boomers Quantity', 0),
                order_data.get('Comments', ''),
                order_data.get('User', '')
            ]
            
            # Add the row
            ws.append_row(row_data)
            
            logger.info(f"Added order for booth {order_data.get('Booth #', '')}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding order: {e}")
            return False
    
    def delete_order(self, sheet_id: str, booth_num: str, item_name: str, 
                     color: str, section: str) -> bool:
        """
        Delete an order from the sheet (adapted from your direct_delete_order function)
        
        Args:
            sheet_id: Google Sheet ID
            booth_num: Booth number
            item_name: Item name
            color: Color
            section: Section name
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.gc:
                return False
            
            # Try both main Orders sheet and section sheet
            worksheets_to_try = ["Orders"]
            if section:
                worksheets_to_try.insert(0, section)  # Try section first
            
            spreadsheet = self.gc.open_by_key(sheet_id)
            
            for worksheet_name in worksheets_to_try:
                try:
                    ws = spreadsheet.worksheet(worksheet_name)
                    data = ws.get_all_values()
                    
                    if not data:
                        continue
                    
                    # Find the row to delete
                    for i, row in enumerate(data[1:], start=2):  # Skip header, start from row 2
                        if (len(row) >= 5 and
                            str(row[0]).strip() == str(booth_num).strip() and  # Booth #
                            str(row[3]).strip() == str(item_name).strip() and  # Item
                            str(row[4]).strip() == str(color).strip()):  # Color
                            
                            # Delete the row
                            ws.delete_rows(i)
                            logger.info(f"Deleted order from {worksheet_name}: booth {booth_num}, item {item_name}")
                            return True
                
                except Exception as e:
                    logger.warning(f"Could not access worksheet {worksheet_name}: {e}")
                    continue
            
            logger.warning(f"Order not found for deletion: booth {booth_num}, item {item_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting order: {e}")
            return False
    
    def get_inventory(self, sheet_id: str) -> List[Dict]:
        """
        Get inventory data
        
        Args:
            sheet_id: Google Sheet ID
            
        Returns:
            List of inventory items
        """
        try:
            inventory_df = self.get_data(sheet_id, "Show Inventory")
            
            if inventory_df.empty:
                return []
            
            # Process inventory (similar to orders)
            inventory_df.columns = inventory_df.iloc[0].str.strip()
            inventory_df = inventory_df[1:]
            inventory_df = inventory_df.reset_index(drop=True)
            
            # Convert to list of dictionaries
            inventory_items = []
            for _, row in inventory_df.iterrows():
                if not row.isna().all():
                    item = {
                        'item': str(row.get('Items', '')).strip(),
                        'load_list': str(row.get('Load List', '')).strip(),
                        'pull_list': str(row.get('Pull List', '')).strip(),
                        'starting_quantity': self._safe_int(row.get('Starting Quantity', '0')),
                        'ordered_items': self._safe_int(row.get('Ordered items', '0')),
                        'damaged_items': self._safe_int(row.get('Damaged Items', '0')),
                        'available_quantity': self._safe_int(row.get('Available Quantity', '0')),
                        'requested_to_warehouse': str(row.get('Requested to the Warehouse', '')).strip(),
                        'requested_date_time': str(row.get('Requested Date and Time', '')).strip()
                    }
                    inventory_items.append(item)
            
            return inventory_items
            
        except Exception as e:
            logger.error(f"Error getting inventory: {e}")
            return []

# Example usage and testing
def test_direct_sheets_integration():
    """Test the Direct Google Sheets integration"""
    
    # Initialize manager
    manager = DirectGoogleSheetsManager()
    
    # Your sheet ID
    sheet_id = "1_yBu2Rx4UGcSL04r0aAMyZDHbpuTKrJK9KavEeanZXs"  # Use your new sheet
    
    try:
        # Test getting all exhibitors
        print("Testing exhibitors retrieval...")
        exhibitors = manager.get_all_exhibitors(sheet_id)
        print(f"Found {len(exhibitors)} exhibitors:")
        for exhibitor in exhibitors[:3]:  # Show first 3
            print(f"  - {exhibitor['name']} (Booth {exhibitor['booth']}): {exhibitor['total_orders']} orders")
        
        # Test getting orders for specific exhibitor
        if exhibitors:
            test_exhibitor = exhibitors[0]['name']
            print(f"\nTesting orders for {test_exhibitor}...")
            orders = manager.get_orders_for_exhibitor(sheet_id, test_exhibitor)
            print(f"Found {len(orders)} orders for {test_exhibitor}")
            
            if orders:
                print("Sample order:")
                print(f"  - {orders[0]['item']} (Status: {orders[0]['status']})")
        
        # Test getting worksheets
        print(f"\nTesting worksheets...")
        worksheets = manager.get_worksheets(sheet_id)
        print(f"Found worksheets: {worksheets}")
        
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    test_direct_sheets_integration()
