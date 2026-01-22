// PayPal Checkout Integration with Server-Side Order Management
const paypalButtons = window.paypal.Buttons({
    style: {
        shape: "rect",
        layout: "vertical",
        color: "gold",
        label: "paypal",
    },
    message: {
        amount: 20,
    },
    
    async createOrder() {
        try {
            const response = await fetch("/api/orders", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    cart: [
                        {
                            id: "pitchai_upgrade",
                            quantity: "1",
                        },
                    ],
                }),
            });

            const orderData = await response.json();

            if (orderData.id) {
                return orderData.id;
            }
            const errorDetail = orderData?.details?.[0];
            const errorMessage = errorDetail
                ? `${errorDetail.issue} ${errorDetail.description} (${orderData.debug_id})`
                : JSON.stringify(orderData);

            throw new Error(errorMessage);
        } catch (error) {
            console.error(error);
            resultMessage(`Could not initiate PayPal Checkout...<br><br>${error}`);
        }
    },
    
    async onApprove(data, actions) {
        try {
            const response = await fetch(
                `/api/orders/${data.orderID}/capture`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                }
            );

            const orderData = await response.json();
            
            // Three cases to handle:
            //   (1) Recoverable INSTRUMENT_DECLINED -> call actions.restart()
            //   (2) Other non-recoverable errors -> Show a failure message
            //   (3) Successful transaction -> Show confirmation or thank you message

            const errorDetail = orderData?.details?.[0];

            if (errorDetail?.issue === "INSTRUMENT_DECLINED") {
                // (1) Recoverable INSTRUMENT_DECLINED -> call actions.restart()
                return actions.restart();
            } else if (errorDetail) {
                // (2) Other non-recoverable errors -> Show a failure message
                throw new Error(
                    `${errorDetail.description} (${orderData.debug_id})`
                );
            } else if (!orderData.purchase_units) {
                throw new Error(JSON.stringify(orderData));
            } else {
                // (3) Successful transaction -> Show confirmation or thank you message
                const transaction =
                    orderData?.purchase_units?.[0]?.payments?.captures?.[0] ||
                    orderData?.purchase_units?.[0]?.payments
                        ?.authorizations?.[0];
                
                // Show success message
                resultMessage(
                    `<div class="success-message">
                        <h3>🎉 Payment Successful!</h3>
                        <p>Your account has been upgraded to Pro access (200/month).</p>
                        <p>Transaction ID: ${transaction.id}</p>
                        <a href="/" class="btn-primary">Start Analyzing</a>
                    </div>`
                );
                
                // Hide PayPal button
                document.getElementById('paypal-button-container').style.display = 'none';
                
                console.log(
                    "Capture result",
                    orderData,
                    JSON.stringify(orderData, null, 2)
                );
            }
        } catch (error) {
            console.error(error);
            resultMessage(
                `<div class="error-message">
                    <h3>❌ Payment Error</h3>
                    <p>Sorry, your transaction could not be processed...</p>
                    <p>${error}</p>
                </div>`
            );
        }
    },

    // Handle errors
    onError: function(err) {
        console.error('PayPal error:', err);
        resultMessage(
            `<div class="error-message">
                <h3>❌ Payment Error</h3>
                <p>An error occurred during payment processing.</p>
                <p>Please try again or contact support.</p>
            </div>`
        );
    },

    // Handle cancellation
    onCancel: function(data) {
        resultMessage(
            `<div class="info-message">
                <h3>⏹️ Payment Cancelled</h3>
                <p>Your payment was cancelled. You can try again anytime.</p>
            </div>`
        );
    }
});

paypalButtons.render("#paypal-button-container");

// Function to show result messages to the user
function resultMessage(message) {
    const container = document.querySelector("#result-message");
    if (container) {
        container.innerHTML = message;
    }
}

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
