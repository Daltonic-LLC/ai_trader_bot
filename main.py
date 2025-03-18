# from services.capture_page import CaptureService
from services.download_file import FileDownloadService

if __name__ == "__main__":
    url = "https://coinmarketcap.com/currencies/xrp/historical-data/"

    # Instantiate the CaptureService
    # service = CaptureService()
    download = FileDownloadService()

    try:
        # Call take_screenshot and execute immediately on running main.py
        # path = service.take_screenshot(url=url)
        # print(f"Screenshot saved to {path}")

        path = download.download_file(url=url)
        print(f"File downloaded to {path}")
    except Exception as e:
        print(f"Error: {e}")
