CargoCheck – Deployment Guide

Project: CargoCheck – Shipment Document Verification System
Maintained by: Sandhya P.
GitHub Repository: https://github.com/Sandhyap10/CargoCheck_Shipments
Live Application: https://cargo-check-shipments.vercel.app
Backend API: https://cargocheck-api.onrender.com
API Documentation: https://cargocheck-api.onrender.com/docs

# CargoCheck – Deployment Guide

## 1. Project Overview

CargoCheck is a shipment document verification and validation application.

The project consists of:

- React frontend built using Vite.
- Python backend built using FastAPI.
- MySQL database.
- PyMuPDF for PDF text extraction.
- Tesseract OCR for scanned documents and images.

## 2. Repository

GitHub: https://github.com/Sandhyap10/CargoCheck_Shipments

The repository contains separate frontend and backend directories, along with the backend Dockerfile and Python dependency list.

## 3. Live Application

| Component | URL |
|---|---|
| Frontend | https://cargo-check-shipments.vercel.app |
| Backend | https://cargocheck-api.onrender.com |
| API Documentation | https://cargocheck-api.onrender.com/docs |

## 4. Prerequisites

Install the following before running the application locally:

- Python 3.11 or compatible version.
- Node.js and npm.
- MySQL Server.
- Git.
- Tesseract OCR.

The backend Dockerfile uses Python 3.11 and installs Tesseract OCR.

## 5. Clone the Repository

```bash
git clone https://github.com/Sandhyap10/CargoCheck_Shipments.git
cd CargoCheck_Shipments
```

## 6. Backend Setup

### Step 1: Navigate to the Backend

```bash
cd backend
```

### Step 2: Create a Virtual Environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

From the repository root:

```bash
pip install -r requirements.txt
```

If the requirements file is not available from the current directory, navigate to the repository root or provide its relative path.

### Step 4: Install Tesseract OCR

Tesseract OCR must be installed on the machine running the backend.

On Windows, install Tesseract and ensure its executable is available to the application. If required, configure the executable path in the OCR configuration used by the backend.

On Linux, Tesseract can be installed using the system package manager.

### Step 5: Configure MySQL

1. Start the MySQL server.
2. Create the application database.
3. Configure the database connection using the settings expected by the backend.
4. Ensure the database user has the required permissions.

Use the actual database configuration keys defined in the backend source code. Do not commit database passwords or other credentials to GitHub.

### Step 6: Start the Backend

From the backend directory:

```bash
uvicorn app.main:app --reload
```

The local API should be available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

## 7. Frontend Setup

### Step 1: Open a New Terminal

Navigate to the frontend directory:

```bash
cd frontend
```

### Step 2: Install Dependencies

```bash
npm install
```

### Step 3: Configure the Backend URL

Create a `.env` file in the frontend directory:

```env
VITE_API_URL=http://127.0.0.1:8000
```

For the deployed application, the configured frontend environment variable is:

```env
VITE_API_URL=https://cargocheck-api.onrender.com
```

Do not commit private credentials or secret values to the repository.

### Step 4: Start the Frontend

```bash
npm run dev
```

Vite will display the local development URL in the terminal, normally:

```text
http://localhost:5173
```

Open the displayed URL in a browser.

## 8. Production Deployment

### Frontend – Vercel

The frontend is deployed on Vercel.

Deployment steps:

1. Connect the GitHub repository to Vercel.
2. Configure the frontend project root directory as `frontend`.
3. Configure the build command according to the frontend package configuration.
4. Set the output directory to `dist`.
5. Add the environment variable:

```env
VITE_API_URL=https://cargocheck-api.onrender.com
```

6. Deploy the application.
7. Redeploy whenever the frontend environment variable changes.

### Backend – Render

The backend is deployed on Render.

The repository contains a Dockerfile that:

- Uses Python 3.11.
- Installs Tesseract OCR and required system libraries.
- Installs Python dependencies.
- Copies the backend application.
- Starts Uvicorn using `app.main:app`.
- Uses the hosting platform's `PORT` value, with `10000` as the fallback.

The backend service URL is:

```text
https://cargocheck-api.onrender.com
```

Configure the database connection and any other required backend settings in the hosting platform's environment configuration, using the exact variable names expected by the application.

## 9. Environment Variables

### Frontend

| Variable | Purpose |
|---|---|
| `VITE_API_URL` | Base URL of the FastAPI backend |

### Backend

The backend requires database connection configuration and may require additional settings for file storage and OCR.

Use the exact variable names defined in the backend configuration. Do not assume variable names or commit their values to the repository.

**Important:** Never include actual passwords, API keys, database credentials, or other secrets in this document.

## 10. Demo Access

The current application does not have a documented demo username or password.

If authentication is not enabled in the deployed build, the application can be accessed directly through the frontend URL.

Frontend:

https://cargo-check-shipments.vercel.app

API documentation:

https://cargocheck-api.onrender.com/docs

## 11. Testing the Application

A basic demonstration workflow is:

1. Open the CargoCheck frontend.
2. View the available shipment records.
3. Select a shipment.
4. Upload the relevant Commercial Invoice, Packing List, or Bill of Lading.
5. Trigger document processing.
6. Review the processing summary.
7. Inspect the extracted information.
8. Review validation results and identify mismatches.

The API can also be tested through the Swagger documentation.

## 12. Storage Limitation

The current backend uses local application file storage for uploaded documents.

On hosting environments with ephemeral filesystems, files may be lost after a restart or redeployment. A database record may remain even when the corresponding original file is no longer available.

For production deployment, configure persistent object storage or a persistent disk and update the document storage implementation accordingly.

## 13. Troubleshooting

### Frontend cannot connect to the backend

- Verify that the backend service is running.
- Check the `VITE_API_URL` value.
- Ensure the frontend has been redeployed after changing its environment variable.
- Check the browser developer console for API errors.

### PDF text is not extracted

- Verify that the uploaded file is a valid PDF.
- Check whether the PDF contains selectable text.
- For scanned documents, verify that Tesseract OCR is installed and configured correctly.

### Original document cannot be previewed

- Check whether the uploaded file still exists in the backend storage directory.
- Re-upload the document if it is missing.
- Check the hosting platform's file persistence configuration.

### Database connection fails

- Verify that MySQL is running.
- Check the configured database host, port, name, username, and password.
- Confirm that the database user has the required permissions.

## 14. Production Readiness Notes

The current deployment is a demonstration environment.

Before using CargoCheck for real shipment operations, implement or verify:

- Persistent document storage.
- Authentication and role-based authorization.
- Secure document access.
- Database backups.
- Audit logging.
- Production monitoring.
- Data protection and hosting-region requirements.
