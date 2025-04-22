import asyncio
import time

import psutil
from fastapi import Request, WebSocket
from fastapi.dependencies.utils import solve_dependencies
from starlette.websockets import WebSocketDisconnect

# Logging
from elysia.api.core.log import logger

# Objects
from elysia.objects import Error


async def help_websocket(websocket: WebSocket, ws_route: callable):
    memory_process = psutil.Process()
    # initial_memory = memory_process.memory_info().rss
    try:
        await websocket.accept()
        while True:
            try:
                # start_time = time.time()
                # Wait for a message from the client
                # logger.info(f"Memory usage before receiving: {psutil.Process().memory_info().rss / 1024 / 1024}MB")
                try:
                    data = None
                    last_communication = time.time()

                    # Custom timeout handler
                    while True:
                        if time.time() - last_communication > 60:
                            # logger.warning("No communication for 60 seconds - sending heartbeat")
                            await websocket.send_json({"type": "heartbeat"})
                            last_communication = time.time()

                        try:
                            # Use a short timeout for receive_json to allow checking the timer
                            data = await asyncio.wait_for(
                                websocket.receive_json(), timeout=1.0
                            )
                            last_communication = time.time()

                            # Process the received data
                            await ws_route(data, websocket)
                            last_communication = (
                                time.time()
                            )  # Update timer after processing

                            # Check if it's a disconnect request
                            if data.get("type") == "disconnect":
                                # logger.info("Received disconnect request")
                                return

                        except asyncio.TimeoutError:
                            # This is just the short receive timeout, not an error condition
                            continue

                except Exception as e:
                    error = Error(text=str(e))
                    error_payload = await error.to_frontend("", "")
                    await websocket.send_json(error_payload)
                    logger.exception(f"Error in websocket communication")

                # logger.info(f"Memory usage after receiving: {psutil.Process().memory_info().rss / 1024 / 1024}MB")
                # logger.info(f"Processing time: {time.time() - start_time}s")

            except WebSocketDisconnect:
                # logger.info("WebSocket disconnected", exc_info=True)
                break  # Exit the loop on disconnect

            except RuntimeError as e:
                if (
                    "Cannot call 'receive' once a disconnect message has been received"
                    in str(e)
                ):
                    # logger.info("WebSocket already disconnected")
                    break  # Exit the loop if the connection is already closed
                else:
                    raise  # Re-raise other RuntimeErrors

            except Exception as e:
                logger.exception(f"Error in WebSocket")
                try:
                    if data and "conversation_id" in data:
                        error = Error(text=str(e))
                        error_payload = await error.to_frontend(data["conversation_id"])
                        await websocket.send_json(error_payload)
                    else:
                        error = Error(text=str(e))
                        error_payload = await error.to_frontend("")
                        await websocket.send_json(error_payload)

                except RuntimeError:
                    logger.warning(
                        "Failed to send error message, WebSocket might be closed"
                    )
                break  # Exit the loop after sending the error message

    except Exception as e:
        logger.warning(f"Closing WebSocket: {str(e)}")
    finally:
        try:
            await websocket.close()
        except RuntimeError:
            logger.debug("WebSocket already closed")
