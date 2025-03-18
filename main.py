from services.download_file import FileDownloadService

if __name__ == "__main__":
    download = FileDownloadService()

    try:
        path = download.download_file(coin="xrp")
        print(f"File downloaded to {path}")
    except Exception as e:
        print(f"Error: {e}")
