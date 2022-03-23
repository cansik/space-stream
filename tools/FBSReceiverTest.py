import time
from spacestream.fbs.FrameBufferSharingClient import FrameBufferSharingClient


def main():
    fbs_client = FrameBufferSharingClient.create()
    fbs_client.setup()

    server_list = fbs_client.get_available_servers()
    print(f"Servers: {', '.join(server_list)}")

    fbs_client.select_server(server_list[0])

    while True:
        frame = fbs_client.receive_texture()
        # print(f"Frame received: {frame}")
        time.sleep(0.5)

    fbs_client.release()


if __name__ == "__main__":
    main()
