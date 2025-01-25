
# Pooler Project Overview

## Purpose
The Pooler project provides a comprehensive solution for managing and validating email configurations, proxies, and logs. It seamlessly integrates a robust backend with a dynamic frontend to offer scalable, efficient, and user-friendly tools for handling network operations.

---

## Architecture Overview

The Pooler system integrates a Django backend with a React frontend. Here’s how the pieces fit together:

1. **Backend**:
   - Handles API logic, background tasks (e.g., Celery), and caching (Redis).
   - Exposes RESTful APIs for frontend interaction.

2. **Frontend**:
   - Built with React, it communicates with the backend using services for data retrieval.
   - Manages state with lightweight hooks using `zustand`.

3. **Integration**:
   - API endpoints in the backend are consumed by services in the frontend, ensuring a seamless flow of data.

**Simplified Flow**:
```
User → Frontend (React) → API Services → Backend (Django) → Redis/Celery → Database
```

---

## Backend Summary

### Technology Stack
- **Framework**: Django
- **Database**: PostgreSQL
- **Caching**: Redis for high-performance data access
- **Task Management**: Celery for asynchronous operations
- **Key Libraries**: `django-environ`, `drf-yasg`, `aiofiles`, `requests`

### Core Functionalities
1. **Apps**:
   - `pooler`: Handles core logic for logs, email validations, and utilities.
   - `proxy`: Manages proxy configurations and related operations.
   - `users`: Provides user authentication and profile management.
   - `telegram`: Integrates Telegram-based utilities.
   - `ufw_manager`: Manages firewall configurations.

2. **Caching**:
   - Redis caching for optimized performance.
   ```python
   CACHES = {
       "default": {
           "BACKEND": "django.core.cache.backends.redis.RedisCache",
           "LOCATION": "redis://redis:6379/1",
       }
   }
   ```

3. **Asynchronous Tasks**:
   - Celery is used to process background tasks such as:
     - Validating SMTP and IMAP configurations.
     - Automating log processing.

4. **API Endpoints**:
   - Exposes RESTful APIs for frontend integration.
   - Handles CRUD operations for:
     - Logs
     - Email configurations
     - Proxy settings
     - User profiles

---

## Frontend Summary

### Technology Stack
- **Framework**: React with TypeScript
- **State Management**: `zustand` for lightweight and modular state handling
- **Key Libraries**: Axios, SCSS, `react-router-dom`, Vite for build optimization

### Core Functionalities
1. **Services**:
   - Provides reusable API methods to interact with the backend.
   - Examples:
     - `useApi.ts`: Fetches logs and manages panels.
     - `useProxy.ts`: Handles proxy configurations.
     - `userService.ts`: Manages user authentication and profiles.

2. **State Management**:
   - `zustand` hooks for managing application state.
   - Key Hooks:
     - `useAppStore`: Maintains global application settings and system status.
     - `useUserStore`: Manages user-specific data like authentication and preferences.

3. **Pages and Components**:
   - **Pages**:
     - Organized under `src/pages` for dynamic routing.
     - Examples: Logs and errors (`logsAndErrors`), profiles (`profile`), and settings.
   - **Components**:
     - Reusable UI elements under `src/components`.
     - Examples: Spinners, modals, and tables.

---

## Developer Workflows

### Setup Instructions
1. **Backend**:
   ```bash
   # Set up the virtual environment and install dependencies
   python -m venv env
   source env/bin/activate
   pip install -r requirements.txt

   # Run the Django development server
   python manage.py runserver
   ```

2. **Frontend**:
   ```bash
   # Install dependencies
   npm install

   # Start the frontend development server
   npm start
   ```

3. **Celery and Redis**:
   ```bash
   # Start Redis server
   docker-compose up redis

   # Start Celery worker
   celery -A pooler worker --loglevel=info
   ```

### Testing Strategy
1. **Backend**:
   - Use Django’s built-in testing framework for unit and integration tests.
   - Example:
     ```python
     def test_view_status_code(self):
         response = self.client.get('/api/logs/')
         self.assertEqual(response.status_code, 200)
     ```

2. **Frontend**:
   - Use Jest and React Testing Library for component and integration tests.
   - Example:
     ```javascript
     import { render, screen } from '@testing-library/react';
     import App from './App';

     test('renders learn react link', () => {
       render(<App />);
       const linkElement = screen.getByText(/learn react/i);
       expect(linkElement).toBeInTheDocument();
     });
     ```

---

## Debugging Tips
1. **Redis Connection Issues**:
   - Ensure Redis is running: `docker ps`.
   - Check configuration in `settings.py`.

2. **Celery Not Processing Tasks**:
   - Confirm the worker is running: `celery -A pooler status`.
   - Check logs for errors: `celery -A pooler worker --loglevel=debug`.

3. **API Failures**:
   - Use `curl` or Postman to test endpoints directly.
   - Debug issues in `views.py`.

---

## Roadmap for Improvement
1. **Scalability**:
   - Introduce GraphQL APIs for flexible queries.
   - Implement horizontal scaling for Redis and Celery.

2. **Enhanced State Management**:
   - Evaluate `Redux Toolkit` for managing complex frontend state.

3. **Performance Optimization**:
   - Add query-level caching in Django.
   - Use lazy-loading for large frontend components.

4. **Monitoring**:
   - Integrate tools like Sentry for error tracking.
   - Add Prometheus/Grafana for real-time performance monitoring.

---

This enhanced document provides a detailed view of the Pooler project’s architecture, workflows, and future direction. 
It’s designed to help developers collaborate effectively and build on a solid foundation.
