"""
Lazarus Engine - Comprehensive Code Generation Prompts
Version 3.0 - Production Grade

This module contains all prompts used by the Lazarus Engine.
Separated for maintainability and easy updates.
"""

def get_code_generation_prompt(plan: str) -> str:
    """
    Returns the comprehensive code generation prompt.
    Handles all edge cases for any tech stack.
    """
    return f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  LAZARUS ENGINE - AUTONOMOUS CODE RESURRECTION SYSTEM                       ║
║  VERSION: 3.0 PRODUCTION                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

ROLE: You are an elite full-stack architect implementing a complete application.

═══════════════════════════════════════════════════════════════════════════════
SECTION 1: ARCHITECTURAL PLAN (From Planning Phase)
═══════════════════════════════════════════════════════════════════════════════

{plan}

═══════════════════════════════════════════════════════════════════════════════
SECTION 2: OUTPUT FORMAT (STRICT XML)
═══════════════════════════════════════════════════════════════════════════════

Output ALL files in this exact XML format:
<file path="modernized_stack/folder/filename.ext">
... complete file content ...
</file>

RULES:
- Each file MUST have the COMPLETE content (NO placeholders like "// ..." or "TODO")
- NO markdown code blocks (```) inside the XML
- One continuous stream of <file> elements
- Every file must be immediately runnable

═══════════════════════════════════════════════════════════════════════════════
SECTION 3: MANDATORY FILE STRUCTURE
═══════════════════════════════════════════════════════════════════════════════

You MUST generate these EXACT files in this EXACT structure:

modernized_stack/
├── backend/
│   ├── main.py              # FastAPI server (REQUIRED)
│   └── requirements.txt     # Python dependencies (REQUIRED)
│
├── frontend/
│   ├── package.json         # Node dependencies (REQUIRED)
│   ├── next.config.mjs      # Next.js config - USE .mjs NOT .ts (REQUIRED)
│   ├── tailwind.config.ts   # Tailwind config (REQUIRED)
│   ├── postcss.config.mjs   # PostCSS config (REQUIRED)
│   ├── tsconfig.json        # TypeScript config (REQUIRED)
│   └── app/
│       ├── layout.tsx       # Root layout - IMPORTS globals.css (REQUIRED)
│       ├── page.tsx         # Home/Landing page (REQUIRED)
│       ├── globals.css      # Global styles with Tailwind (REQUIRED)
│       └── [other pages as needed based on plan]
│
└── docker-compose.yml       # Container orchestration (REQUIRED)

═══════════════════════════════════════════════════════════════════════════════
⚠️ CRITICAL: SANDBOX COMPATIBILITY - FILE PATH RESTRICTIONS ⚠️
═══════════════════════════════════════════════════════════════════════════════

The sandbox runs in a bash shell. File paths with special characters will BREAK!

🚫 FORBIDDEN CHARACTERS IN FILE/FOLDER NAMES:
- NO parentheses: ( )
- NO brackets: [ ] {{ }}
- NO spaces
- NO special chars: $ & * ? ! | ; < > ` ' "
- NO @ or # symbols

❌ WRONG FILE PATHS (WILL CRASH SANDBOX):
- app/(auth)/login/page.tsx       ← Parentheses break bash!
- app/[id]/page.tsx               ← Brackets break bash!
- components/my component.tsx      ← Spaces break bash!
- routes/@modal/page.tsx          ← @ symbol breaks bash!

✅ CORRECT FILE PATHS:
- app/auth/login/page.tsx         ← Use simple folder names
- app/user-detail/page.tsx        ← Use hyphens for readability
- app/dashboard/page.tsx          ← Simple alphanumeric names
- components/user-card.tsx        ← Hyphens are safe
- app/product_list/page.tsx       ← Underscores are safe

DYNAMIC ROUTES - Use simple naming:
- Instead of app/[id]/page.tsx    → app/detail/page.tsx (use URL params in code)
- Instead of app/(group)/auth     → app/auth (just flatten it)

ALWAYS USE: Only alphanumeric characters, hyphens (-), underscores (_), and dots (.)

═══════════════════════════════════════════════════════════════════════════════
SECTION 4: BACKEND REQUIREMENTS (FastAPI - PYTHON)
═══════════════════════════════════════════════════════════════════════════════

FILE: modernized_stack/backend/main.py

MANDATORY TEMPLATE - Copy and extend:

```python
from fastapi import FastAPI, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lazarus-engine")

app = FastAPI(
    title="Lazarus Backend",
    description="Resurrected by Lazarus Engine",
    version="1.0.0"
)

# CRITICAL: CORS middleware for sandbox compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MODELS ============
# Add Pydantic models based on your plan

class HealthResponse(BaseModel):
    status: str
    service: str

# ============ ENDPOINTS ============

@app.get("/", response_model=HealthResponse)
def health_check():
    \"\"\"Health check endpoint for sandbox detection.\"\"\"
    return {{"status": "online", "service": "lazarus-backend"}}

@app.get("/api/health")
def api_health():
    return {{"message": "Backend is running", "version": "1.0.0"}}

# Add more endpoints based on the architectural plan...

# ============ STARTUP ============

if __name__ == "__main__":
    logger.info("Starting Lazarus Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

FILE: modernized_stack/backend/requirements.txt

MUST include these base dependencies:
```
fastapi
uvicorn
pydantic
python-multipart
```

Add based on features:
- Authentication: passlib[bcrypt], python-jose[cryptography]
- Database: sqlalchemy, databases
- Email: email-validator
- HTTP client: httpx, requests

═══════════════════════════════════════════════════════════════════════════════
SECTION 5: FRONTEND REQUIREMENTS (Next.js 15 - TYPESCRIPT)
═══════════════════════════════════════════════════════════════════════════════

▓▓▓ FILE: modernized_stack/frontend/package.json ▓▓▓

EXACT CONTENT (copy this structure):
```json
{{
  "name": "lazarus-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {{
    "dev": "next dev",
    "build": "next build",
    "start": "next start -p 3000",
    "lint": "next lint"
  }},
  "dependencies": {{
    "next": "15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "lucide-react": "^0.400.0"
  }},
  "devDependencies": {{
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "typescript": "^5",
    "tailwindcss": "^3.4.0",
    "postcss": "^8",
    "autoprefixer": "^10"
  }}
}}
```

▓▓▓ FILE: modernized_stack/frontend/next.config.mjs ▓▓▓

CRITICAL: Use .mjs extension, NOT .ts (Next.js doesn't support TS config)
```javascript
/** @type {{import('next').NextConfig}} */
const nextConfig = {{
  output: 'standalone',
  reactStrictMode: true,
  eslint: {{
    ignoreDuringBuilds: true,
  }},
  typescript: {{
    ignoreBuildErrors: true,
  }},
}};

export default nextConfig;
```

▓▓▓ FILE: modernized_stack/frontend/tailwind.config.ts ▓▓▓

```typescript
import type {{ Config }} from 'tailwindcss';

const config: Config = {{
  content: [
    './app/**/*.{{js,ts,jsx,tsx,mdx}}',
    './components/**/*.{{js,ts,jsx,tsx,mdx}}',
  ],
  theme: {{
    extend: {{
      colors: {{
        // Customize based on user preferences from plan
        primary: '#06b6d4',    // cyan-500
        secondary: '#8b5cf6',  // violet-500
        accent: '#f59e0b',     // amber-500
        dark: '#0a0a0a',
        light: '#fafafa',
      }},
      animation: {{
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      }},
      keyframes: {{
        glow: {{
          '0%': {{ boxShadow: '0 0 5px currentColor' }},
          '100%': {{ boxShadow: '0 0 20px currentColor, 0 0 30px currentColor' }},
        }},
      }},
    }},
  }},
  plugins: [],
}};

export default config;
```

▓▓▓ FILE: modernized_stack/frontend/postcss.config.mjs ▓▓▓

```javascript
const config = {{
  plugins: {{
    tailwindcss: {{}},
    autoprefixer: {{}},
  }},
}};

export default config;
```

▓▓▓ FILE: modernized_stack/frontend/tsconfig.json ▓▓▓

```json
{{
  "compilerOptions": {{
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{{ "name": "next" }}],
    "paths": {{ "@/*": ["./*"] }}
  }},
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}}
```

▓▓▓ FILE: modernized_stack/frontend/app/layout.tsx ▓▓▓

CRITICAL: This file MUST import globals.css for Tailwind to work!

```typescript
import type {{ Metadata }} from 'next';
import {{ Inter }} from 'next/font/google';
import './globals.css';

const inter = Inter({{ subsets: ['latin'] }});

export const metadata: Metadata = {{
  title: 'Resurrected Application',
  description: 'Modernized by Lazarus Engine',
}};

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode;
}}) {{
  return (
    <html lang="en" className="dark">
      <body className={{`${{inter.className}} bg-dark text-light antialiased min-h-screen`}}>
        {{children}}
      </body>
    </html>
  );
}}
```

▓▓▓ FILE: modernized_stack/frontend/app/globals.css ▓▓▓

MUST START WITH THESE THREE LINES:
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

/* ============ Base Styles ============ */
html, body {{
  min-height: 100vh;
  scroll-behavior: smooth;
}}

/* ============ Custom Utilities ============ */
@layer utilities {{
  .text-gradient {{
    @apply bg-clip-text text-transparent bg-gradient-to-r from-cyan-400 to-purple-600;
  }}
  
  .glass {{
    @apply bg-white/5 backdrop-blur-lg border border-white/10;
  }}
  
  .glow-cyan {{
    box-shadow: 0 0 20px rgba(6, 182, 212, 0.3);
  }}
  
  .glow-purple {{
    box-shadow: 0 0 20px rgba(139, 92, 246, 0.3);
  }}
}}

/* ============ Animations ============ */
@keyframes float {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-10px); }}
}}

.animate-float {{
  animation: float 3s ease-in-out infinite;
}}
```

▓▓▓ FILE: modernized_stack/frontend/app/page.tsx ▓▓▓

TEMPLATE with API integration:

```typescript
'use client';

import {{ useState, useEffect }} from 'react';

export default function HomePage() {{
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // CRITICAL: Always use environment variable for API URL
  const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
  
  useEffect(() => {{
    checkBackendConnection();
  }}, []);
  
  const checkBackendConnection = async () => {{
    try {{
      const response = await fetch(`${{API_URL}}/api/health`);
      if (response.ok) {{
        const result = await response.json();
        console.log('Backend connected:', result);
      }}
    }} catch (err) {{
      console.log('Backend connection pending...');
    }}
  }};
  
  // ... implement the rest based on the plan
  
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-900">
      <div className="container mx-auto px-4 py-16">
        {{/* Your UI implementation here */}}
      </div>
    </main>
  );
}}
```

═══════════════════════════════════════════════════════════════════════════════
SECTION 6: TYPESCRIPT SYNTAX RULES (CRITICAL)
═══════════════════════════════════════════════════════════════════════════════

You MUST use TypeScript syntax, NOT Python syntax:

| WRONG (Python)          | CORRECT (TypeScript)              |
|-------------------------|-----------------------------------|
| name: str               | name: string                      |
| count: int              | count: number                     |
| active: bool            | active: boolean                   |
| items: List[str]        | items: string[]                   |
| data: Dict              | data: Record<string, any>         |
| Optional[str]           | string | null                     |
| func(x: int) -> str     | function func(x: number): string  |

INTERFACE EXAMPLE:
```typescript
interface User {{
  id: number;
  name: string;
  email: string;
  isActive: boolean;
  roles: string[];
  metadata: Record<string, any> | null;
}}
```

STATE TYPES:
```typescript
const [items, setItems] = useState<string[]>([]);
const [user, setUser] = useState<User | null>(null);
const [count, setCount] = useState<number>(0);
```

═══════════════════════════════════════════════════════════════════════════════
SECTION 7: COMMON PITFALLS TO AVOID
═══════════════════════════════════════════════════════════════════════════════

❌ DO NOT:
1. Use next.config.ts (use .mjs instead)
2. Forget to import globals.css in layout.tsx
3. Hardcode API URLs (use process.env.NEXT_PUBLIC_API_URL)
4. Use @app.on_event decorator (deprecated in FastAPI)
5. Forget CORS middleware in backend
6. Forget health check endpoint at /
7. Use Python type hints in TypeScript code
8. Leave placeholder comments like "// ... rest of code"
9. Forget 'use client' directive for interactive components
10. Use incompatible React/Next versions
11. Forget to bind uvicorn to 0.0.0.0 (not 127.0.0.1)
12. Use curl in sandbox (use Python urllib instead)

✅ DO:
1. Include ALL config files (postcss, tailwind, tsconfig)
2. Add comprehensive error handling
3. Include loading states in all forms
4. Use proper semantic HTML
5. Make designs responsive (mobile-first)
6. Add proper TypeScript types
7. Include meaningful comments
8. Use Lucide React for icons
9. Add input validation on forms
10. Use try/catch for all API calls

═══════════════════════════════════════════════════════════════════════════════
SECTION 8: DESIGN REQUIREMENTS
═══════════════════════════════════════════════════════════════════════════════

Based on the user preferences in the plan, implement:

1. COLOR SCHEME: Extract from plan and add to tailwind.config.ts
2. TYPOGRAPHY: Use Inter font (included in layout via next/font)
3. SPACING: Consistent padding/margins (use Tailwind spacing scale)
4. COMPONENTS: Cards, buttons, inputs with visual feedback
5. ANIMATIONS: Subtle transitions (hover effects, loading states)
6. DARK MODE: Default dark theme with proper contrast

DEFAULT MODERN STYLE (Cyberpunk/Glassmorphism):
- Dark background: bg-gray-900, bg-black
- Gradient accents: from-cyan-400 to-purple-600
- Glassmorphism: backdrop-blur-lg, bg-white/5
- Rounded corners: rounded-lg, rounded-xl
- Gradient text: text-gradient (custom class)
- Smooth transitions: transition-all duration-300
- Glowing effects: shadow-lg, glow-cyan (custom class)

BUTTON PATTERNS:
```tsx
<button className="px-6 py-3 bg-gradient-to-r from-cyan-500 to-purple-600 
  text-white font-semibold rounded-lg hover:opacity-90 transition-all 
  disabled:opacity-50 disabled:cursor-not-allowed">
  Click Me
</button>
```

INPUT PATTERNS:
```tsx
<input 
  className="w-full px-4 py-3 bg-white/5 border border-white/10 
  rounded-lg text-white placeholder-gray-400 focus:border-cyan-500 
  focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all"
  placeholder="Enter value..."
/>
```

CARD PATTERNS:
```tsx
<div className="glass rounded-xl p-6 hover:border-cyan-500/50 transition-all">
  {{/* Card content */}}
</div>
```

═══════════════════════════════════════════════════════════════════════════════
SECTION 9: DOCKER COMPOSE
═══════════════════════════════════════════════════════════════════════════════

FILE: modernized_stack/docker-compose.yml

```yaml
version: '3.8'

services:
  backend:
    build: 
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped
```

═══════════════════════════════════════════════════════════════════════════════
SECTION 10: FINAL CHECKLIST (Verify Before Output)
═══════════════════════════════════════════════════════════════════════════════

□ Backend has CORS middleware with allow_origins=["*"]
□ Backend has health check at GET / returning JSON
□ Backend uses uvicorn.run(app, host="0.0.0.0", port=8000)
□ Backend has requirements.txt with all dependencies
□ Frontend package.json has Next.js 15 and React 19
□ Frontend next.config.mjs uses .mjs extension (NOT .ts)
□ Frontend next.config.mjs has eslint and typescript ignoreBuildErrors
□ Frontend layout.tsx imports ./globals.css
□ Frontend globals.css starts with @tailwind base/components/utilities
□ Frontend uses process.env.NEXT_PUBLIC_API_URL for all API calls
□ All TypeScript uses correct syntax (string, number, boolean)
□ All files are COMPLETE with no placeholders
□ tsconfig.json is included
□ postcss.config.mjs is included
□ tailwind.config.ts is included with correct content paths
□ All interactive components have 'use client' directive

═══════════════════════════════════════════════════════════════════════════════
NOW GENERATE THE COMPLETE FILE STREAM
═══════════════════════════════════════════════════════════════════════════════

Output ALL files now in XML format. Include EVERY required file with COMPLETE content.
Do not omit any file. Do not use placeholders. Every file must be production-ready.
"""
