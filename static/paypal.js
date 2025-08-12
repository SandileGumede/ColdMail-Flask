// PayPal Checkout Integration
paypal.Buttons({
    // Sets up the transaction when a payment button is clicked
    createOrder: function(data, actions) {
        return actions.order.create({
            purchase_units: [{
                amount: {
                    value: '20.00' // $20.00 for unlimited analyses
                },
                description: 'PitchAI Unlimited Analyses Upgrade',
                custom_id: 'pitchai_upgrade'
            }]
        });
    },

    // Finalize the transaction after payer approval
    onApprove: function(data, actions) {
        return actions.order.capture().then(function(details) {
            // Successful payment
            console.log('Payment completed successfully:', details);
            
            // Send payment details to your Flask backend
            fetch('/paypal_webhook', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    orderID: data.orderID,
                    payerID: data.payerID,
                    paymentDetails: details
                })
            })
            .then(response => {
                if (response.status === 401) {
                    // User not authenticated
                    throw new Error('Please log in to complete your purchase');
                }
                return response.json();
            })
            .then(result => {
                if (result.success) {
                    // Show success message
                    document.getElementById('result-message').innerHTML = 
                        '<div class="success-message">' +
                        '<h3>🎉 Payment Successful!</h3>' +
                        '<p>Your account has been upgraded to unlimited analyses.</p>' +
                        '<p>Transaction ID: ' + data.orderID + '</p>' +
                        '<a href="/" class="btn-primary">Start Analyzing</a>' +
                        '</div>';
                    
                    // Hide PayPal button
                    document.getElementById('paypal-button-container').style.display = 'none';
                } else {
                    throw new Error(result.message || 'Payment verification failed');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                if (error.message === 'Please log in to complete your purchase') {
                    document.getElementById('result-message').innerHTML = 
                        '<div class="error-message">' +
                        '<h3>🔐 Authentication Required</h3>' +
                        '<p>Please log in to complete your purchase.</p>' +
                        '<a href="/login" class="btn-primary">Log In</a>' +
                        '</div>';
                } else {
                    document.getElementById('result-message').innerHTML = 
                        '<div class="error-message">' +
                        '<h3>⚠️ Payment Verification Error</h3>' +
                        '<p>Your payment was successful, but we encountered an issue verifying it.</p>' +
                        '<p>Please contact support with your transaction ID: ' + data.orderID + '</p>' +
                        '</div>';
                }
            });
        });
    },

    // Handle errors
    onError: function(err) {
        console.error('PayPal error:', err);
        document.getElementById('result-message').innerHTML = 
            '<div class="error-message">' +
            '<h3>❌ Payment Error</h3>' +
            '<p>An error occurred during payment processing.</p>' +
            '<p>Please try again or contact support.</p>' +
            '</div>';
    },

    // Handle cancellation
    onCancel: function(data) {
        document.getElementById('result-message').innerHTML = 
            '<div class="info-message">' +
            '<h3>⏹️ Payment Cancelled</h3>' +
            '<p>Your payment was cancelled. You can try again anytime.</p>' +
            '</div>';
    }
}).render('#paypal-button-container');

// Add some styling for the result messages
const style = document.createElement('style');
style.textContent = `
    .success-message {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 20px;
        border-radius: 5px;
        margin: 20px 0;
        text-align: center;
    }
    
    .error-message {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        padding: 20px;
        border-radius: 5px;
        margin: 20px 0;
        text-align: center;
    }
    
    .info-message {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        padding: 20px;
        border-radius: 5px;
        margin: 20px 0;
        text-align: center;
    }
    
    .btn-primary {
        display: inline-block;
        background: #007bff;
        color: white;
        padding: 10px 20px;
        text-decoration: none;
        border-radius: 5px;
        margin-top: 10px;
    }
    
    .btn-primary:hover {
        background: #0056b3;
    }
`;
document.head.appendChild(style);
