# PayPal Integration Guide

## Overview
This guide explains how to use the new PayPal checkout integration in your PitchAI application.

## Features
- **Modern PayPal JS SDK Integration**: Uses PayPal's latest JavaScript SDK for seamless checkout
- **Real-time Payment Processing**: Payments are processed immediately without page redirects
- **Automatic Account Upgrade**: Users are automatically upgraded to unlimited analyses upon successful payment
- **Fallback Support**: Maintains the legacy PayPal redirect method as a backup

## How It Works

### 1. User Flow
1. User clicks "Upgrade" from the main page
2. User sees two payment options:
   - **New PayPal Checkout** (recommended)
   - **Legacy PayPal** (fallback)
3. User clicks "New PayPal Checkout"
4. PayPal button appears on the checkout page
5. User completes payment through PayPal
6. Account is automatically upgraded
7. User sees success message and can start analyzing

### 2. Technical Implementation
- **Frontend**: PayPal JS SDK handles payment processing
- **Backend**: Flask webhook endpoint verifies payment and upgrades user account
- **Database**: User's `is_paid` field is updated to `True`

## Files Created/Modified

### New Files
- `templates/paypal_checkout.html` - PayPal checkout page
- `static/paypal.js` - PayPal integration JavaScript
- `PAYPAL_INTEGRATION.md` - This documentation

### Modified Files
- `app.py` - Added new routes and webhook handler
- `templates/upgrade.html` - Added link to new checkout
- `static/style.css` - Added PayPal-specific styling

## Routes

### `/upgrade`
- Shows both payment options
- Links to new PayPal checkout

### `/paypal-checkout`
- Direct access to PayPal checkout page
- Requires user authentication

### `/paypal_webhook`
- Handles payment verification from frontend
- Updates user account status
- Returns success/error response

## Environment Variables Required

Make sure these are set in your `.env` file:
```bash
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
```

## Testing

### Development
1. Start your Flask application
2. Navigate to `/upgrade`
3. Click "New PayPal Checkout"
4. Use PayPal sandbox credentials for testing

### Production
1. Ensure PayPal credentials are set to live mode
2. Test with small amounts first
3. Monitor webhook responses

## Security Features

- **Authentication Required**: All payment routes require user login
- **Payment Verification**: Backend verifies payment status before upgrading
- **Session Management**: Secure session handling for user authentication
- **Error Handling**: Comprehensive error handling for failed payments

## Troubleshooting

### Common Issues

1. **PayPal Button Not Loading**
   - Check if `PAYPAL_CLIENT_ID` is set correctly
   - Verify internet connection
   - Check browser console for JavaScript errors

2. **Payment Verification Fails**
   - Check Flask logs for webhook errors
   - Verify user authentication
   - Check database connection

3. **User Not Upgraded**
   - Check if `mark_paid()` method exists in User model
   - Verify webhook endpoint is working
   - Check database for user record updates

### Debug Mode
Enable Flask debug mode to see detailed error messages:
```python
app.run(debug=True)
```

## Support

If you encounter issues:
1. Check the Flask application logs
2. Verify PayPal credentials
3. Test with PayPal sandbox first
4. Check browser console for JavaScript errors

## Future Enhancements

- Add payment history tracking
- Implement subscription-based pricing
- Add multiple payment methods
- Enhanced error reporting
- Payment analytics dashboard
