"""
Admin dashboard routes for AutoHVAC founder analytics
Provides business metrics and user management interface
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlmodel import Session, select, func, and_, or_
from app.database import get_session
from app.models.user import UserModel, SubscriptionStatus

router = APIRouter()
security = HTTPBasic()

# Simple password protection
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "autohvac2024")

def authenticate_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Simple HTTP Basic Auth for admin access"""
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    admin_user: str = Depends(authenticate_admin),
    session: Session = Depends(get_session)
):
    """Main admin dashboard with business metrics"""
    
    # Get comprehensive analytics
    analytics = await get_user_analytics(session)
    recent_users = await get_recent_users(session, limit=10)
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AutoHVAC Admin Dashboard</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            :root {{
                /* AutoHVAC Brand Colors */
                --brand-25: #FAFBFC;
                --brand-50: #F8FAFC;
                --brand-100: #E8ECF2;
                --brand-200: #D1DAE6;
                --brand-300: #9FB3CF;
                --brand-400: #6D8BB8;
                --brand-500: #204274;
                --brand-600: #1A355D;
                --brand-700: #052047;
                --brand-800: #031633;
                --brand-900: #020D1F;
                
                /* Accent Orange */
                --accent-orange: #F26419;
                --accent-light: #FFB584;
                
                /* Premium Gray Scale */
                --gray-25: #FCFCFD;
                --gray-50: #F9FAFB;
                --gray-100: #F2F4F7;
                --gray-200: #EAECF0;
                --gray-300: #D0D5DD;
                --gray-400: #98A2B3;
                --gray-500: #667085;
                --gray-600: #475467;
                --gray-700: #344054;
                --gray-800: #1D2939;
                --gray-900: #101828;
                
                /* Premium Shadows */
                --shadow-xs: 0px 1px 2px 0px rgba(16, 24, 40, 0.05);
                --shadow-sm: 0px 1px 2px 0px rgba(16, 24, 40, 0.06), 0px 1px 3px 0px rgba(16, 24, 40, 0.10);
                --shadow-md: 0px 2px 4px -2px rgba(16, 24, 40, 0.06), 0px 4px 8px -2px rgba(16, 24, 40, 0.10);
                --shadow-lg: 0px 4px 6px -2px rgba(16, 24, 40, 0.03), 0px 12px 16px -4px rgba(16, 24, 40, 0.08);
                --shadow-xl: 0px 8px 8px -4px rgba(16, 24, 40, 0.03), 0px 20px 24px -4px rgba(16, 24, 40, 0.08);
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{ 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-feature-settings: 'cv02', 'cv03', 'cv04', 'cv11';
                -webkit-font-smoothing: antialiased;
                -moz-osx-font-smoothing: grayscale;
                background: var(--gray-25);
                color: var(--gray-900);
                font-size: 1rem;
                line-height: 1.5;
                letter-spacing: -0.011em;
                min-height: 100vh;
            }}
            
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 2rem;
            }}
            
            .header {{ 
                background: linear-gradient(135deg, var(--brand-700) 0%, var(--brand-500) 100%);
                padding: 2rem; 
                border-radius: 1rem; 
                margin-bottom: 2rem; 
                box-shadow: var(--shadow-lg);
                color: white;
                position: relative;
                overflow: hidden;
            }}
            
            .header::before {{
                content: "";
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: radial-gradient(ellipse at top right, rgba(242, 100, 25, 0.1) 0%, transparent 50%);
                pointer-events: none;
            }}
            
            .header-content {{
                position: relative;
                z-index: 1;
            }}
            
            .header h1 {{ 
                font-size: 2.25rem;
                line-height: 2.75rem;
                font-weight: 600;
                letter-spacing: -0.02em;
                margin-bottom: 0.5rem;
            }}
            
            .header p {{
                color: rgba(255, 255, 255, 0.8);
                font-size: 1.125rem;
                margin-bottom: 1.5rem;
            }}
            
            .header-actions {{
                display: flex;
                align-items: center;
                gap: 1rem;
                flex-wrap: wrap;
            }}
            
            .refresh-btn {{ 
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                color: white;
                padding: 0.75rem 1.25rem;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 0.5rem;
                cursor: pointer;
                font-weight: 500;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                font-size: 0.875rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
                letter-spacing: -0.006em;
            }}
            
            .refresh-btn:hover {{
                background: rgba(255, 255, 255, 0.2);
                transform: translateY(-1px);
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            }}
            
            .refresh-btn svg {{
                opacity: 0.8;
            }}
            
            .timestamp {{ 
                color: rgba(255, 255, 255, 0.7); 
                font-size: 0.875rem;
            }}
            
            .metrics {{ 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); 
                gap: 1.5rem; 
                margin-bottom: 2rem; 
            }}
            
            .metric-card {{ 
                background: white; 
                padding: 1.5rem; 
                border-radius: 0.75rem; 
                box-shadow: var(--shadow-xs);
                text-align: center;
                transition: all 0.2s;
                border: 1px solid var(--gray-200);
            }}
            
            .metric-card:hover {{
                box-shadow: var(--shadow-md);
                transform: translateY(-2px);
            }}
            
            .metric-number {{ 
                font-size: 2.5rem; 
                font-weight: 700; 
                color: var(--brand-600);
                line-height: 1;
                margin-bottom: 0.5rem;
            }}
            
            .metric-label {{ 
                color: var(--gray-600); 
                font-weight: 500;
                font-size: 0.875rem;
                letter-spacing: -0.006em;
            }}
            
            .section {{ 
                background: white; 
                padding: 1.5rem; 
                border-radius: 0.75rem; 
                margin-bottom: 1.5rem; 
                box-shadow: var(--shadow-xs);
                border: 1px solid var(--gray-200);
            }}
            
            .section h2 {{
                font-size: 1.25rem;
                font-weight: 600;
                color: var(--gray-900);
                margin-bottom: 1rem;
                letter-spacing: -0.01em;
            }}
            
            .user-table {{ 
                width: 100%; 
                border-collapse: collapse;
                font-size: 0.875rem;
            }}
            
            .user-table th, .user-table td {{ 
                text-align: left; 
                padding: 0.75rem; 
                border-bottom: 1px solid var(--gray-200); 
            }}
            
            .user-table th {{ 
                background: var(--gray-50); 
                font-weight: 600;
                color: var(--gray-700);
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            
            .user-table tbody tr:hover {{
                background: var(--gray-25);
            }}
            
            .status-badge {{ 
                padding: 0.25rem 0.5rem; 
                border-radius: 0.375rem; 
                font-size: 0.75rem; 
                font-weight: 500;
                border: 1px solid;
            }}
            
            .status-active {{ 
                background: #D1FAE5; 
                color: #065F46; 
                border-color: #A7F3D0;
            }}
            
            .status-none {{ 
                background: var(--gray-100); 
                color: var(--gray-700);
                border-color: var(--gray-200);
            }}
            
            .status-expired {{ 
                background: #FEE2E2; 
                color: #991B1B;
                border-color: #FECACA;
            }}
            
            .status-trialing {{
                background: #DBEAFE;
                color: #1E40AF;
                border-color: #BFDBFE;
            }}
            
            .status-canceled {{
                background: #FEF3C7;
                color: #92400E;
                border-color: #FDE68A;
            }}
            
            .search-container {{
                position: relative;
                margin-bottom: 1.5rem;
            }}
            
            .search-icon {{
                position: absolute;
                left: 1rem;
                top: 50%;
                transform: translateY(-50%);
                color: var(--gray-400);
                pointer-events: none;
            }}
            
            .search-box {{ 
                width: 100%; 
                padding: 0.875rem 1rem 0.875rem 2.75rem;
                border: 1px solid var(--gray-200); 
                border-radius: 0.75rem; 
                font-size: 0.875rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                background: var(--gray-25);
                letter-spacing: -0.006em;
            }}
            
            .search-box:focus {{
                outline: none;
                border-color: var(--brand-400);
                box-shadow: 0 0 0 4px rgba(32, 66, 116, 0.08);
                background: white;
            }}
            
            .search-box::placeholder {{
                color: var(--gray-500);
            }}
            
            .breakdown-grid {{
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); 
                gap: 1rem;
            }}
            
            .breakdown-card {{
                padding: 1rem; 
                border-radius: 0.5rem; 
                text-align: center;
                border: 1px solid;
                transition: all 0.2s;
            }}
            
            .breakdown-card:hover {{
                transform: translateY(-1px);
                box-shadow: var(--shadow-sm);
            }}
            
            .breakdown-number {{
                font-weight: 700; 
                font-size: 1.25rem;
                margin-bottom: 0.25rem;
            }}
            
            .breakdown-label {{
                color: var(--gray-600); 
                text-transform: capitalize;
                font-size: 0.875rem;
                font-weight: 500;
            }}
            
            .quick-actions {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 1rem;
            }}
            
            .action-link {{
                display: flex;
                align-items: center;
                gap: 0.75rem;
                padding: 1rem 1.25rem;
                background: var(--gray-25);
                border: 1px solid var(--gray-200);
                border-radius: 0.75rem;
                color: var(--gray-700);
                text-decoration: none;
                font-weight: 500;
                font-size: 0.875rem;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                letter-spacing: -0.006em;
            }}
            
            .action-link:hover {{
                background: white;
                border-color: var(--brand-300);
                color: var(--brand-700);
                transform: translateY(-1px);
                box-shadow: var(--shadow-sm);
            }}
            
            .action-link svg {{
                opacity: 0.7;
                transition: opacity 0.2s;
            }}
            
            .action-link:hover svg {{
                opacity: 1;
            }}
            
            @media (max-width: 768px) {{
                .container {{ padding: 1rem; }}
                .header {{ padding: 1.5rem; }}
                .metrics {{ grid-template-columns: 1fr; }}
                .breakdown-grid {{ grid-template-columns: repeat(2, 1fr); }}
                .quick-actions {{ flex-direction: column; gap: 0.75rem; }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="header-content">
                    <h1>AutoHVAC Intelligence Center</h1>
                    <p>Advanced analytics and customer intelligence powered by AI</p>
                    <div class="header-actions">
                        <button class="refresh-btn" onclick="window.location.reload()">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M23 4v6h-6M1 20v-6h6M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.64A9 9 0 0 1 3.51 15"/>
                            </svg>
                            Refresh Analytics
                        </button>
                        <div class="timestamp">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </div>
                </div>
            </div>
            
            <div class="metrics">
                <div class="metric-card">
                    <div class="metric-number">{analytics['total_users']}</div>
                    <div class="metric-label">Total Users</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics['new_users_this_week']}</div>
                    <div class="metric-label">New This Week</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics['paying_customers']}</div>
                    <div class="metric-label">Paying Customers</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics['conversion_rate']:.1f}%</div>
                    <div class="metric-label">Conversion Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics['avg_conversion_time_days']}</div>
                    <div class="metric-label">Avg. Conversion Time (Days)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-number">{analytics['high_value_users']}</div>
                    <div class="metric-label">High-Value Users</div>
                </div>
            </div>
            
            <div class="section">
                <h2>Advanced Intelligence Metrics</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem;">
                    <div style="background: #F0F9FF; color: #0369A1; padding: 1.25rem; border-radius: 0.75rem; text-align: center; border: 1px solid #BAE6FD;">
                        <div style="font-weight: 700; font-size: 1.5rem; margin-bottom: 0.5rem;">{analytics['fast_converters']}</div>
                        <div style="font-size: 0.875rem; font-weight: 500;">Fast Converters (≤24h)</div>
                    </div>
                    <div style="background: #ECFDF5; color: #065F46; padding: 1.25rem; border-radius: 0.75rem; text-align: center; border: 1px solid #A7F3D0;">
                        <div style="font-weight: 700; font-size: 1.5rem; margin-bottom: 0.5rem;">{analytics['email_verification_rate']:.1f}%</div>
                        <div style="font-size: 0.875rem; font-weight: 500;">Email Verification Rate</div>
                    </div>
                    <div style="background: #FEF7FF; color: #7C2D12; padding: 1.25rem; border-radius: 0.75rem; text-align: center; border: 1px solid #E9D5FF;">
                        <div style="font-weight: 700; font-size: 1.5rem; margin-bottom: 0.5rem;">{analytics['unique_ip_addresses']}</div>
                        <div style="font-size: 0.875rem; font-weight: 500;">Geographic Reach</div>
                    </div>
                    <div style="background: #FFFBEB; color: #92400E; padding: 1.25rem; border-radius: 0.75rem; text-align: center; border: 1px solid #FDE68A;">
                        <div style="font-weight: 700; font-size: 1.5rem; margin-bottom: 0.5rem;">{analytics['at_risk_users']}</div>
                        <div style="font-size: 0.875rem; font-weight: 500;">At-Risk Users</div>
                    </div>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                <div class="section">
                    <h2>Conversion Intelligence</h2>
                    <div style="display: grid; gap: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Total Converters</span>
                            <span style="color: var(--brand-600); font-weight: 700;">{analytics['total_converters']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Median Time to Convert</span>
                            <span style="color: var(--brand-600); font-weight: 700;">{analytics['median_conversion_time_days']} days</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Geographic Diversity</span>
                            <span style="color: var(--brand-600); font-weight: 700;">{analytics['geographic_diversity_score']:.1f}%</span>
                        </div>
                    </div>
                </div>
                
                <div class="section">
                    <h2>User Health Monitor</h2>
                    <div style="display: grid; gap: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Active This Week</span>
                            <span style="color: #059669; font-weight: 700;">{analytics['active_users_week']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Active This Month</span>
                            <span style="color: #0369A1; font-weight: 700;">{analytics['active_users_month']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem; background: var(--gray-50); border-radius: 0.5rem;">
                            <span style="color: var(--gray-700); font-weight: 500;">Dormant Users</span>
                            <span style="color: #DC2626; font-weight: 700;">{analytics['dormant_users']}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>Growth Trajectory</h2>
                <div style="background: white; padding: 1.5rem; border-radius: 0.75rem; border: 1px solid var(--gray-200); margin-bottom: 1.5rem;">
                    <canvas id="growthChart" width="400" height="120"></canvas>
                </div>
            </div>
            
            <div class="section">
                <h2>Customer Intelligence Overview</h2>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1.5rem;">
                    {get_subscription_breakdown_html(analytics['subscription_breakdown'])}
                </div>
            </div>
            
            <div class="section">
                <h2>Customer Activity Stream</h2>
                <div class="search-container">
                    <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="11" cy="11" r="8"/>
                        <path d="m21 21-4.35-4.35"/>
                    </svg>
                    <input type="text" class="search-box" placeholder="Search customers by email address..." 
                           onkeyup="filterUsers(this.value)">
                </div>
                <table class="user-table" id="userTable">
                    <thead>
                        <tr>
                            <th>Email</th>
                            <th>Name</th>
                            <th>Signup Date</th>
                            <th>Status</th>
                            <th>Reports</th>
                            <th>Free Used</th>
                        </tr>
                    </thead>
                    <tbody>
                        {get_users_table_html(recent_users)}
                    </tbody>
                </table>
            </div>
            
            <div class="section">
                <h2>Intelligence Operations</h2>
                <div class="quick-actions">
                    <a href="/admin/users/export" class="action-link">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14,2 14,8 20,8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                            <polyline points="10,9 9,9 8,9"/>
                        </svg>
                        Export Customer Data
                    </a>
                    <a href="/admin/analytics" class="action-link">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="22,12 18,12 15,21 9,3 6,12 2,12"/>
                        </svg>
                        Advanced Analytics
                    </a>
                    <a href="/admin/search" class="action-link">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="M21 21l-4.35-4.35"/>
                        </svg>
                        Deep Search
                    </a>
                </div>
            </div>
        </div>
        
        <script>
            // Growth Chart
            const ctx = document.getElementById('growthChart').getContext('2d');
            const growthData = {analytics['growth_data']};
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: growthData.dates,
                    datasets: [
                        {{
                            label: 'Paying Subscribers',
                            data: growthData.subscribers,
                            borderColor: '#204274',
                            backgroundColor: 'rgba(32, 66, 116, 0.1)',
                            borderWidth: 3,
                            fill: true,
                            tension: 0.4,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            pointBackgroundColor: '#204274',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2
                        }},
                        {{
                            label: 'Total Users',
                            data: growthData.total_users,
                            borderColor: '#F26419',
                            backgroundColor: 'rgba(242, 100, 25, 0.1)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.4,
                            pointRadius: 3,
                            pointHoverRadius: 5,
                            pointBackgroundColor: '#F26419',
                            pointBorderColor: '#ffffff',
                            pointBorderWidth: 2,
                            borderDash: [5, 5]
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top',
                            align: 'end',
                            labels: {{
                                usePointStyle: true,
                                font: {{
                                    family: 'Inter',
                                    size: 12,
                                    weight: '500'
                                }},
                                color: '#475467',
                                padding: 20
                            }}
                        }},
                        tooltip: {{
                            backgroundColor: 'rgba(255, 255, 255, 0.95)',
                            titleColor: '#111827',
                            bodyColor: '#374151',
                            borderColor: '#D1D5DB',
                            borderWidth: 1,
                            cornerRadius: 8,
                            displayColors: true,
                            font: {{
                                family: 'Inter'
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            display: true,
                            grid: {{
                                display: false
                            }},
                            ticks: {{
                                font: {{
                                    family: 'Inter',
                                    size: 11
                                }},
                                color: '#9CA3AF',
                                maxTicksLimit: 10
                            }}
                        }},
                        y: {{
                            display: true,
                            beginAtZero: true,
                            grid: {{
                                color: 'rgba(209, 213, 219, 0.3)',
                                drawBorder: false
                            }},
                            ticks: {{
                                font: {{
                                    family: 'Inter',
                                    size: 11
                                }},
                                color: '#9CA3AF',
                                precision: 0
                            }}
                        }}
                    }},
                    interaction: {{
                        intersect: false,
                        mode: 'index'
                    }}
                }}
            }});
            
            function filterUsers(searchTerm) {{
                const table = document.getElementById('userTable');
                const rows = table.getElementsByTagName('tr');
                
                for (let i = 1; i < rows.length; i++) {{
                    const email = rows[i].getElementsByTagName('td')[0].textContent;
                    if (email.toLowerCase().includes(searchTerm.toLowerCase())) {{
                        rows[i].style.display = '';
                    }} else {{
                        rows[i].style.display = 'none';
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    return html_content

def get_subscription_breakdown_html(breakdown):
    """Generate HTML for subscription status breakdown"""
    html = ""
    status_config = {
        "none": {"bg": "var(--gray-100)", "text": "var(--gray-700)", "border": "var(--gray-200)", "label": "Free Users"},
        "active": {"bg": "#ECFDF5", "text": "#065F46", "border": "#A7F3D0", "label": "Active Subscriptions"}, 
        "expired": {"bg": "#FEF2F2", "text": "#991B1B", "border": "#FECACA", "label": "Expired"},
        "canceled": {"bg": "#FFFBEB", "text": "#92400E", "border": "#FDE68A", "label": "Canceled"},
        "trialing": {"bg": "#EFF6FF", "text": "#1E40AF", "border": "#BFDBFE", "label": "Trial Period"}
    }
    
    for status, count in breakdown.items():
        config = status_config.get(status, status_config["none"])
        html += f"""
        <div style="background: {config['bg']}; color: {config['text']}; padding: 1.25rem; border-radius: 0.75rem; text-align: center; border: 1px solid {config['border']}; transition: all 0.2s;">
            <div style="font-weight: 700; font-size: 1.5rem; line-height: 1; margin-bottom: 0.5rem;">{count}</div>
            <div style="font-size: 0.875rem; font-weight: 500; letter-spacing: -0.006em;">{config['label']}</div>
        </div>
        """
    return html

def get_users_table_html(users):
    """Generate HTML table rows for users"""
    html = ""
    for user in users:
        status_class = f"status-{user.subscription_status}"
        free_used = "✅" if user.free_report_used else "❌"
        
        html += f"""
        <tr>
            <td>{user.email}</td>
            <td>{user.name or 'Not provided'}</td>
            <td>{user.created_at.strftime('%Y-%m-%d') if user.created_at else 'Unknown'}</td>
            <td><span class="status-badge {status_class}">{user.subscription_status}</span></td>
            <td>{user.total_reports_generated}</td>
            <td>{free_used}</td>
        </tr>
        """
    return html

async def get_conversion_analytics(session: Session):
    """Advanced conversion funnel analytics"""
    
    # Time to conversion analysis - users who converted from free to paid
    converted_users = session.exec(
        select(UserModel).where(
            and_(
                UserModel.free_report_used == True,
                UserModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
            )
        )
    ).all()
    
    conversion_times = []
    for user in converted_users:
        if user.free_report_used_at and user.subscription_started_at:
            time_diff = user.subscription_started_at - user.free_report_used_at
            conversion_times.append(time_diff.total_seconds() / 86400)  # Convert to days
    
    # Calculate conversion time metrics
    if conversion_times:
        avg_conversion_time = sum(conversion_times) / len(conversion_times)
        median_conversion_time = sorted(conversion_times)[len(conversion_times) // 2]
        fast_converters = len([t for t in conversion_times if t <= 1])  # Within 24 hours
    else:
        avg_conversion_time = median_conversion_time = fast_converters = 0
    
    # Email verification rate
    total_users = session.exec(select(func.count(UserModel.id))).first()
    verified_users = session.exec(
        select(func.count(UserModel.id)).where(UserModel.email_verified == True)
    ).first()
    verification_rate = (verified_users / total_users * 100) if total_users > 0 else 0
    
    return {
        'avg_conversion_time_days': round(avg_conversion_time, 1),
        'median_conversion_time_days': round(median_conversion_time, 1),
        'fast_converters': fast_converters,
        'total_converters': len(conversion_times),
        'email_verification_rate': round(verification_rate, 1)
    }

async def get_geographic_analytics(session: Session):
    """Geographic insights from IP addresses"""
    
    # Get IP address distribution (simplified - you'd want proper GeoIP lookup)
    ip_data = session.exec(
        select(UserModel.ip_address, func.count(UserModel.id))
        .where(UserModel.ip_address.isnot(None))
        .group_by(UserModel.ip_address)
    ).all()
    
    total_with_ip = sum(count for _, count in ip_data)
    unique_locations = len(ip_data)
    
    # Detect potential duplicate IPs (simple fraud indicator)
    duplicate_ips = len([ip for ip, count in ip_data if count > 1])
    
    # Geographic diversity score (higher = more diverse)
    geo_diversity = (unique_locations / total_with_ip * 100) if total_with_ip > 0 else 0
    
    return {
        'unique_ip_addresses': unique_locations,
        'users_with_ip_data': total_with_ip,
        'duplicate_ip_addresses': duplicate_ips,
        'geographic_diversity_score': round(geo_diversity, 1)
    }

async def get_user_health_metrics(session: Session):
    """User engagement and health scoring"""
    
    # Activity metrics
    week_ago = datetime.now() - timedelta(days=7)
    month_ago = datetime.now() - timedelta(days=30)
    
    # Recent activity
    active_this_week = session.exec(
        select(func.count(UserModel.id)).where(UserModel.last_login_at >= week_ago)
    ).first()
    
    active_this_month = session.exec(
        select(func.count(UserModel.id)).where(UserModel.last_login_at >= month_ago)
    ).first()
    
    # Dormant users (no login in 30+ days)
    dormant_users = session.exec(
        select(func.count(UserModel.id)).where(
            or_(
                UserModel.last_login_at < month_ago,
                UserModel.last_login_at.is_(None)
            )
        )
    ).first()
    
    # High-value users (paid + active)
    high_value_users = session.exec(
        select(func.count(UserModel.id)).where(
            and_(
                UserModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
                UserModel.last_login_at >= week_ago
            )
        )
    ).first()
    
    # At-risk users (paid but inactive)
    at_risk_users = session.exec(
        select(func.count(UserModel.id)).where(
            and_(
                UserModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING]),
                or_(
                    UserModel.last_login_at < week_ago,
                    UserModel.last_login_at.is_(None)
                )
            )
        )
    ).first()
    
    return {
        'active_users_week': active_this_week or 0,
        'active_users_month': active_this_month or 0,
        'dormant_users': dormant_users or 0,
        'high_value_users': high_value_users or 0,
        'at_risk_users': at_risk_users or 0
    }

async def get_growth_chart_data(session: Session):
    """Get subscriber growth data for charting"""
    
    # Get the earliest subscription date to determine chart range
    earliest_sub = session.exec(
        select(UserModel.subscription_started_at)
        .where(UserModel.subscription_started_at.isnot(None))
        .order_by(UserModel.subscription_started_at.asc())
        .limit(1)
    ).first()
    
    if not earliest_sub:
        # No subscribers yet - return empty data
        return {'dates': [], 'subscribers': [], 'total_users': []}
    
    # Generate daily data points from earliest subscription to now
    start_date = earliest_sub.date()
    end_date = datetime.now().date()
    
    dates = []
    subscribers = []
    total_users = []
    
    current_date = start_date
    while current_date <= end_date:
        # Count active subscribers on this date
        subscriber_count = session.exec(
            select(func.count(UserModel.id)).where(
                and_(
                    UserModel.subscription_started_at <= datetime.combine(current_date, datetime.min.time()),
                    or_(
                        UserModel.subscription_expires_at.is_(None),
                        UserModel.subscription_expires_at > datetime.combine(current_date, datetime.min.time())
                    ),
                    UserModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
                )
            )
        ).first() or 0
        
        # Count total users on this date
        total_user_count = session.exec(
            select(func.count(UserModel.id)).where(
                UserModel.created_at <= datetime.combine(current_date, datetime.min.time())
            )
        ).first() or 0
        
        dates.append(current_date.strftime('%Y-%m-%d'))
        subscribers.append(subscriber_count)
        total_users.append(total_user_count)
        
        # Move to next day (sample every 3 days to reduce data points for performance)
        current_date += timedelta(days=3)
    
    return {
        'dates': dates,
        'subscribers': subscribers, 
        'total_users': total_users
    }

async def get_user_analytics(session: Session):
    """Get comprehensive user analytics"""
    
    # Basic metrics
    total_users = session.exec(select(func.count(UserModel.id))).first()
    
    week_ago = datetime.now() - timedelta(days=7)
    new_users_this_week = session.exec(
        select(func.count(UserModel.id)).where(UserModel.created_at >= week_ago)
    ).first()
    
    paying_customers = session.exec(
        select(func.count(UserModel.id)).where(
            UserModel.subscription_status.in_([SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
        )
    ).first()
    
    free_reports_used = session.exec(
        select(func.count(UserModel.id)).where(UserModel.free_report_used == True)
    ).first()
    
    total_reports = session.exec(
        select(func.sum(UserModel.total_reports_generated))
    ).first() or 0
    
    # Subscription breakdown
    subscription_breakdown = {}
    for status in SubscriptionStatus:
        count = session.exec(
            select(func.count(UserModel.id)).where(UserModel.subscription_status == status)
        ).first()
        subscription_breakdown[status.value] = count
    
    # Advanced Analytics
    conversion_analytics = await get_conversion_analytics(session)
    geographic_analytics = await get_geographic_analytics(session)
    user_health_metrics = await get_user_health_metrics(session)
    growth_data = await get_growth_chart_data(session)
    
    # Calculate conversion rate
    conversion_rate = (paying_customers / total_users * 100) if total_users > 0 else 0
    
    return {
        'total_users': total_users,
        'new_users_this_week': new_users_this_week,
        'paying_customers': paying_customers,
        'free_reports_used': free_reports_used,
        'total_reports': total_reports,
        'conversion_rate': conversion_rate,
        'subscription_breakdown': subscription_breakdown,
        'growth_data': growth_data,
        **conversion_analytics,
        **geographic_analytics,
        **user_health_metrics
    }

async def get_recent_users(session: Session, limit: int = 10):
    """Get recent users with key information"""
    users = session.exec(
        select(UserModel)
        .order_by(UserModel.created_at.desc())
        .limit(limit)
    ).all()
    return users

@router.get("/analytics")
async def detailed_analytics(
    admin_user: str = Depends(authenticate_admin),
    session: Session = Depends(get_session)
):
    """Detailed analytics endpoint (JSON)"""
    analytics = await get_user_analytics(session)
    return analytics

@router.get("/users/search")
async def search_users(
    email: Optional[str] = None,
    admin_user: str = Depends(authenticate_admin),
    session: Session = Depends(get_session)
):
    """Search users by email"""
    if not email:
        return {"error": "Email parameter required"}
    
    users = session.exec(
        select(UserModel).where(UserModel.email.ilike(f"%{email}%"))
    ).all()
    
    return {"users": [
        {
            "email": user.email,
            "name": user.name,
            "created_at": user.created_at,
            "subscription_status": user.subscription_status,
            "total_reports": user.total_reports_generated,
            "free_report_used": user.free_report_used
        }
        for user in users
    ]}

@router.get("/users/export")
async def export_users_csv(
    admin_user: str = Depends(authenticate_admin),
    session: Session = Depends(get_session)
):
    """Export all users as CSV"""
    from fastapi.responses import StreamingResponse
    import io
    import csv
    
    users = session.exec(select(UserModel)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # CSV Header
    writer.writerow([
        'Email', 'Name', 'Created At', 'Subscription Status', 
        'Total Reports', 'Free Report Used', 'Last Login'
    ])
    
    # CSV Data
    for user in users:
        writer.writerow([
            user.email,
            user.name or '',
            user.created_at.isoformat() if user.created_at else '',
            user.subscription_status,
            user.total_reports_generated,
            user.free_report_used,
            user.last_login_at.isoformat() if user.last_login_at else ''
        ])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=autohvac_users.csv"}
    )