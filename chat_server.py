# chat_server.py
import asyncio
import websockets
import json
import logging

# Configure logging for better visibility
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set to store all connected WebSocket clients
CONNECTED_CLIENTS = set()

# Asynchronous function to handle incoming WebSocket connections
async def websocket_handler(websocket, path):
    """
    Handles a new WebSocket connection, registers the client,
    and processes incoming messages.
    """
    # Register the new client
    CONNECTED_CLIENTS.add(websocket)
    logging.info(f"Client connected: {websocket.remote_address}. Total clients: {len(CONNECTED_CLIENTS)}")

    try:
        # Loop indefinitely to receive messages from this client
        async for message in websocket:
            logging.info(f"Received message from {websocket.remote_address}: {message}")
            
            # Parse the incoming message (expecting JSON with 'user' and 'text')
            try:
                data = json.loads(message)
                user = data.get('user', 'Anonymous')
                text = data.get('text', '')
                
                if text:
                    # Format the message for broadcasting
                    broadcast_message = json.dumps({"user": user, "text": text})
                    
                    # Broadcast the message to all other connected clients
                    await broadcast(broadcast_message)
                else:
                    logging.warning(f"Received empty message text from {user} ({websocket.remote_address})")

            except json.JSONDecodeError:
                logging.error(f"Invalid JSON received from {websocket.remote_address}: {message}")
            except Exception as e:
                logging.error(f"Error processing message from {websocket.remote_address}: {e}")

    except websockets.exceptions.ConnectionClosedOK:
        logging.info(f"Client disconnected gracefully: {websocket.remote_address}")
    except websockets.exceptions.ConnectionClosedError as e:
        logging.warning(f"Client disconnected with error: {websocket.remote_address} - {e}")
    except Exception as e:
        logging.error(f"Unexpected error in websocket_handler for {websocket.remote_address}: {e}")
    finally:
        # Unregister the client when they disconnect
        if websocket in CONNECTED_CLIENTS:
            CONNECTED_CLIENTS.remove(websocket)
            logging.info(f"Client disconnected. Total clients: {len(CONNECTED_CLIENTS)}")

async def broadcast(message):
    """
    Sends a message to all connected clients.
    """
    if not CONNECTED_CLIENTS:
        logging.info("No clients to broadcast to.")
        return

    # Create a list of tasks to send the message to each client
    # Use a copy of the set to avoid "set changed size during iteration" if a client disconnects
    send_tasks = []
    for client in list(CONNECTED_CLIENTS):
        try:
            send_tasks.append(asyncio.create_task(client.send(message)))
        except Exception as e:
            logging.error(f"Error scheduling message to client: {e}")

    # Execute all send tasks concurrently
    if send_tasks:
        done, pending = await asyncio.wait(send_tasks, timeout=5)
        for task in pending:
            task.cancel() # Cancel tasks that didn't complete within timeout
        for task in done:
            if task.exception():
                logging.error(f"Error sending message to a client: {task.exception()}")
    else:
        logging.info("No active clients to send message to.")

async def main():
    """
    Main function to start the WebSocket server.
    """
    # Define the host and port for the WebSocket server
    # 0.0.0.0 means listen on all available network interfaces
    HOST = '0.0.0.0'
    PORT = 8765 # Choose a different port than your HTTP server (e.g., 8000)

    logging.info(f"Starting WebSocket server on ws://{HOST}:{PORT}")
    
    # Start the WebSocket server
    async with websockets.serve(websocket_handler, HOST, PORT):
        # Keep the server running indefinitely
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server stopped by user (Ctrl+C).")
    except Exception as e:
        logging.critical(f"Server crashed: {e}", exc_info=True)
