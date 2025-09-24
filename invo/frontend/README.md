# GST Service Center Frontend

A Next.js frontend application for the GST Service Center invoice management system.

## Features

- 🔐 JWT-based authentication
- 📊 Dashboard with business statistics
- 📄 Invoice management (Create, Read, Update, Delete)
- 🔍 Search and filter invoices
- 📱 Responsive design
- 🎨 Modern UI with Tailwind CSS

## Tech Stack

- **Framework**: Next.js 14 with TypeScript
- **Styling**: Tailwind CSS
- **Forms**: React Hook Form
- **HTTP Client**: Axios
- **State Management**: React Query
- **Icons**: Lucide React
- **Notifications**: React Hot Toast

## Getting Started

### Development

1. Install dependencies:

```bash
npm install
```

2. Start the development server:

```bash
npm run dev
```

3. Open [http://localhost:3000](http://localhost:3000) in your browser.

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up frontend

# Or run the entire stack
docker-compose up
```

## Environment Variables

- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)

## Default Login Credentials

For development and testing:

- **Username**: admin@example.com
- **Password**: admin123

## Project Structure

```
frontend/
├── src/
│   ├── app/                 # Next.js app directory
│   │   ├── login/          # Login page
│   │   ├── layout.tsx      # Root layout
│   │   └── page.tsx        # Home page
│   ├── components/         # React components
│   │   ├── Dashboard.tsx   # Main dashboard
│   │   ├── InvoiceForm.tsx # Invoice form modal
│   │   └── LoadingSpinner.tsx
│   └── lib/                # Utilities
│       ├── api.ts          # API client
│       └── auth-context.tsx # Auth context
├── public/                 # Static assets
├── package.json
├── tailwind.config.js
├── next.config.js
└── Dockerfile
```

## API Integration

The frontend integrates with the FastAPI backend for:

- User authentication
- Invoice CRUD operations
- Business statistics
- System health monitoring

## Building for Production

```bash
npm run build
npm start
```

Or use the production Dockerfile:

```bash
docker build -t gst-frontend .
docker run -p 3000:3000 gst-frontend
```
