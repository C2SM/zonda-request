---
name: ICON External Parameter Request
about: Use this template to submit a request for an ICON grid and external parameters
labels: data request

---

# ICON External Parameter Request

## Instructions

1. Give this issue a meaningful title (e.g. including domain name, grid specifications, project, etc.).

2. Replace `PASTE_YOUR_REQUEST_HERE` with your request that you copied to clipboard:
```json
PASTE_YOUR_REQUEST_HERE
```

3. Click on the "Preview" tab (top left) to verify that the JSON format of your request is correctly formatted and displayed within a code block.

4. Click on "Create" below to submit the data request.

Zonda Request will now process your data based on your request. Once the processing is successful, it will post a link in the issue you have just created. The processed data will be available under that link for up to **7 days**.

If you encounter any problems, please add the label ![Static Badge](https://img.shields.io/badge/help_wanted-orange) to the issue. Make sure you post all relevant information from the logfiles in the issue directly.

## Status Labels

Labels reflect the current state of your request:

![Static Badge](https://img.shields.io/badge/submitted-yellow) - Your request is currently under processing. Please wait for further updates.

![Static Badge](https://img.shields.io/badge/completed-green) - Your request has been successfully processed. You can download your data using the provided link.

![Static Badge](https://img.shields.io/badge/failed-red) - Unfortunately, your request could not be processed. Please refer to the log files in the zip file at the download link for more details.

![Static Badge](https://img.shields.io/badge/aborted-lightgray) - Your request was aborted. This might be due to a timeout. Please try again or contact support if the problem persists.
