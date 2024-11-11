---
name: Data Request
about: Use this template to submit a request for data processing
labels: data request

---

# Zephyr Data Request

## Instructions

1. Give this issue a meaningful title.
2. Replace `PASTE_YOUR_REQUEST_HERE` with your request that you copied to clipboard:
```json
PASTE_YOUR_REQUEST_HERE
```
3. Click on "Preview" to verify that the JSON format of your request is correctly formatted and displayed within a code block.
4. Click on "Submit new issue".

Zephyr Data Request will now process your data based on the request you provided here. Once the processing is successful, it will post a link in this issue. 
The processed data will be available under that link for up to **7 days**.

If you encounter any problems, please open a discussion in the [C2SM forum](https://github.com/C2SM/Tasks-Support/discussions).

## Status Labels

Labels reflect the current state of your request:

![Static Badge](https://img.shields.io/badge/submitted-yellow) - Your request is currently under processing. Please wait for further updates.

![Static Badge](https://img.shields.io/badge/completed-green) - Your request has been successfully processed. You can download your data using the provided link.

![Static Badge](https://img.shields.io/badge/failed-red) - Unfortunately, your request could not be processed. Please refer to the log files in the zip file at the download link for more details.

![Static Badge](https://img.shields.io/badge/aborted-lightgray) - Your request was aborted. This might be due to a timeout. Please try again or contact support if the problem persists.
