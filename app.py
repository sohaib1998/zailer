from flask import Flask, request, jsonify
import requests
import json
import os

app = Flask(__name__)

SESSION_FILE = 'sessions.json'

#retrieve and load sessioins from file
if os.path.exists(SESSION_FILE):
    with open(SESSION_FILE, 'r') as f:
        sessions = json.load(f)
else:
    sessions = {}

@app.route('/new-order', methods=['POST'])
def new_order():
    data = request.get_json()
    buyer_name = data['buyerName']
    whatsapp_number = data['whatsappNumber']
    product_name = data['productName']
    order_details = data['orderDetails']

    #all the buyers informations need to be stored in the sessions
    sessions[whatsapp_number] = {
        'buyer_name': buyer_name,
        'product_name': product_name,
        'order_details': order_details
    }

    # sessions to file
    with open(SESSION_FILE, 'w') as f:
        json.dump(sessions, f)

    # first message to send to the buyer
    initial_message = f"Salam {buyer_name}, yalah dwezti m3ana wahd l order fih {product_name}. wach bghiti t confirmer wla 3ndek chi sou2al."

    # Send the message via ultramsg.com
    send_message_via_ultramsg(whatsapp_number, initial_message)

    return jsonify({'status': 'Message sent'}), 200


@app.route('/receive-message', methods=['POST'])
def receive_message():
    print("=== Webhook Received ===")
    print("Request Form Data:", request.form)
    print("Request JSON Data:", request.json)
    data = request.form

    #check if the event retrieved is a message
    event = data.get('event')
    if event != 'message':
        return 'OK', 200  # if it is not messsage ignore it

    sender = data.get('from')
    message = data.get('body')

    print(f"Sender: {sender}, Message: {message}")

    # Load sessions from file
    with open(SESSION_FILE, 'r') as f:
        sessions = json.load(f)
    print("Loaded Sessions:", sessions)

    # Retrieve buyer information
    buyer_info = sessions.get(sender)

    if buyer_info:
        response = get_llm_response(sender, message, buyer_info)
    else:
        response = "Sorry, we couldn't find your order details. Please contact support."

    # Send the response back to the user
    send_message_via_ultramsg(sender, response)

    return 'OK', 200


def send_message_via_ultramsg(to, message):
    url = 'https://api.ultramsg.com/instance96818/messages/chat'
    payload = {
        'token': 'akh39cwvpxnuiauv',
        'to': to,
        'body': message
    }
    response = requests.post(url, data=payload)

    print("UltraMsg Response Status:", response.status_code)
    print("UltraMsg Response Body:", response.text)

    return response.json()


def get_llm_response(sender, message, buyer_info):
    payload = {
        'sender': sender,
        'message': message,
        'buyerName': buyer_info['buyer_name'],
        'productName': buyer_info['product_name'],
        'orderDetails': buyer_info['order_details']
    }

    try:
        llm_response = requests.post('https://your-llm-endpoint.com/generate', json=payload)
        llm_response.raise_for_status()
        llm_response_json = llm_response.json()
        response_text = llm_response_json.get('response', 'Sorry, I did not understand that.')
    except requests.exceptions.RequestException as e:
        print(f"Error calling LLM API: {e}")
        response_text = "Sorry, we're experiencing technical difficulties. Please try again later."

    return response_text


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
