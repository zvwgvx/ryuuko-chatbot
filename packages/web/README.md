# Ryuuko Web Dashboard

This package contains the frontend web dashboard for the Ryuuko project. It is built with React and Vite.

## Getting Started

### Prerequisites

*   Node.js and npm (or a compatible package manager)
*   The Ryuuko API service running locally

### Installation

1.  **Navigate to the web package directory:**
    ```bash
    cd packages/web
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

### Usage

To run the web dashboard in development mode, use the following command from the `packages/web` directory:

```bash
npm run dev
```

The dashboard will be available at `http://localhost:5173`.

The development server is configured to proxy API requests from `/api` to the backend server running at `http://127.0.0.1:8000`, avoiding CORS issues.

### Building for Production

To create a production build of the application, run:

```bash
npm run build
```

The optimized static assets will be placed in the `dist/` directory.