import os

import zmq
from backend.isyntax_reader import IsyntaxSlide


def server_handler():
    port = os.environ["WS_ISYNTAX_PORT"]
    print(f"starting isyntax backend...")
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{port}")
    print(f"zeromq server binding to *:{port}")

    while True:
        message = socket.recv_json()

        mapped_filepath = "/data" + message["filepath"]
        reader = IsyntaxSlide(mapped_filepath, message["slide_id"])

        if message["req"] == "verification":
            socket.send_json(reader.result)
        elif message["req"] == "get_info":
            socket.send_json(reader.get_info())
        elif message["req"] == "LABEL":
            socket.send(reader.get_label())
        elif message["req"] == "MACRO":
            socket.send(reader.get_macro())
        elif message["req"] == "get_region":
            resp, image_array, width, height = reader.get_region(
                message["level"],
                message["start_x"],
                message["start_y"],
                message["size_x"],
                message["size_y"],
            )
            send_array_response(socket, resp, image_array, width, height)
        elif message["req"] == "get_tile":
            resp, image_array, width, height = reader.get_tile(message["level"], message["tile_x"], message["tile_y"])
            send_array_response(socket, resp, image_array, width, height)
        elif message["req"] == "get_thumbnail":
            resp, image_array, width, height = reader.get_thumbnail(message["max_x"], message["max_y"])
            send_array_response(socket, resp, image_array, width, height)
        else:
            req = message["req"]
            socket.send_json(
                {
                    "rep": "error",
                    "status_code": 422,
                    "detail": f"Invalid request ({req})",
                }
            )


def send_array_response(socket, resp, image_array, width, height):
    if resp["rep"] == "success":
        socket.send_json(
            {
                "rep": "success",
                "status_code": 200,
                "detail": f"",
                "width": width,
                "height": height,
            },
            zmq.SNDMORE,
        )
        socket.send(image_array)
    else:
        socket.send_json(resp)
        socket.send(None)


if __name__ == "__main__":
    server_handler()
