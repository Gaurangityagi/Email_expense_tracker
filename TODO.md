# TODO: Fix Order Analysis Page - Empty Order Lists

## Problem Analysis
- Order analysis page shows empty lists because backend is not extracting order data from emails.
- CSV download contains "undefined" values, indicating expenses array is empty or malformed.
- Email parsing logic in `email_processing.py` may not match actual email content from sources like Swiggy, Zomato, etc.

## Plan
1. **Update Amount Extraction Patterns**: Enhance regex patterns in `extract_order_info` method to better match real email formats from food delivery and e-commerce sources.
2. **Add Debugging Logs**: Insert print statements to log email processing steps, body content, and extraction attempts for troubleshooting.
3. **Improve Data Validation**: Ensure date and amount parsing handles edge cases and converts data correctly.
4. **Test Backend Endpoint**: Run the backend and test the `/analyze_emails` endpoint with sample data.
5. **Verify Frontend Integration**: Check that frontend correctly displays the returned data.

## Dependent Files
- `backend/email_processing.py`: Update extraction logic and add debugging.
- `backend/app.py`: Ensure data processing and response formatting is correct.

## Followup Steps
- [x] After code changes, restart the backend server.
- [x] Test the order analysis feature with valid credentials and selected sources.
- [x] Check console logs for debugging output to identify any remaining issues.
- [x] Fixed Swiggy amount extraction to prioritize 'Amount Payable' over 'Order Total'
- [x] Added proper company categorization for consistent display
- [ ] If issues persist, may need to inspect actual email content or adjust patterns further.
