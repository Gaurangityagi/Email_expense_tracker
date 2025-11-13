# Updated TODO for Monthly Budget Persistence and Refund Fix

## Persistence for Monthly Budget
- [x] Modify backend/app.py to add load_user_data() and save_user_data() functions using JSON file (user_data.json)
- [x] Integrate load_user_data() on app startup to restore user_data from file
- [x] Update /set_budget endpoint to save user_data to file after setting budget
- [ ] Test: Set budget, restart backend, verify budget persists

## Fix Refund/Cancellation Counting in Expenses
- [x] Enhance backend/email_processing.py to detect refunds/cancellations more comprehensively
  - Check subject and body for keywords: "refund", "cancelled", "returned", "credit", "reversal", "void", "failed", "declined"
  - Apply to all sources, not just Amazon and BookMyShow
- [x] Update parse_emails method to skip emails with refund indicators
- [ ] Test: Process emails with refunds, ensure they're excluded from totals

## Testing
- [ ] Test budget persistence across app restarts
- [ ] Test refund exclusion with sample emails
- [ ] Verify accurate expense calculations
