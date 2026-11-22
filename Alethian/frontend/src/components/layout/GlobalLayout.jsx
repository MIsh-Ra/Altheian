import { useNavigate, useLocation } from 'react-router-dom';
import { Shield, LayoutDashboard, Settings, LogOut, Moon, Sun } from 'lucide-react';
import { useTheme } from '../ThemeContext';

export default function GlobalLayout({ children }) {
    const navigate = useNavigate();
    const location = useLocation();
    const { theme, toggleTheme } = useTheme();
    const user = JSON.parse(localStorage.getItem('alethian_user') || '{}');

    const handleLogout = () => {
        localStorage.removeItem('alethian_token');
        localStorage.removeItem('alethian_user');
        navigate('/login');
    };

    const navItems = [
        { path: '/dashboard', label: 'Faculty dashboard', icon: LayoutDashboard },
        { path: '/admin', label: 'System configuration', icon: Settings }
    ];

    return (
        <div className="flex h-screen w-full bg-background overflow-hidden text-on-background print:h-auto print:overflow-visible print:block">
            {/* Desktop App Sidebar: 256px, 4px grid, quiet graphite surfaces */}
            <aside className="w-64 bg-surface-container-low border-r border-ghost flex flex-col justify-between p-4 flex-none select-none print:hidden">
                <div className="space-y-6">
                    {/* Brand Row */}
                    <div className="flex items-center space-x-2.5 px-2 py-1">
                        <div className="w-7 h-7 rounded bg-primary text-on-primary flex items-center justify-center">
                            <Shield className="w-4 h-4" strokeWidth={1.75} />
                        </div>
                        <span className="text-base font-semibold tracking-tight text-on-surface">Alethian</span>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-on-surface-variant bg-surface-container px-1.5 py-0.5 rounded">v3.0</span>
                    </div>

                    {/* Navigation */}
                    <nav className="space-y-1">
                        {navItems.map((item) => {
                            const Icon = item.icon;
                            const isActive = location.pathname.startsWith(item.path);
                            return (
                                <button
                                    key={item.path}
                                    onClick={() => navigate(item.path)}
                                    className={`w-full flex items-center space-x-2.5 px-3 py-2 rounded text-xs font-medium transition-colors ${
                                        isActive
                                            ? 'bg-surface text-on-surface shadow-sm border border-ghost'
                                            : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                                    }`}
                                >
                                    <Icon className="w-4 h-4 text-on-surface-variant" strokeWidth={1.5} />
                                    <span>{item.label}</span>
                                </button>
                            );
                        })}
                    </nav>
                </div>

                {/* Footer Controls & User */}
                <div className="space-y-2 pt-4 border-t border-ghost">
                    <button
                        onClick={toggleTheme}
                        className="w-full flex items-center justify-between px-3 py-2 rounded text-xs font-medium text-on-surface-variant hover:bg-surface-container hover:text-on-surface transition-colors"
                    >
                        <span className="flex items-center space-x-2.5">
                            {theme === 'dark' ? <Moon className="w-4 h-4" strokeWidth={1.5} /> : <Sun className="w-4 h-4" strokeWidth={1.5} />}
                            <span>{theme === 'dark' ? 'Dark theme' : 'Light theme'}</span>
                        </span>
                        <span className="text-[10px] font-mono text-on-surface-variant/70">⌥T</span>
                    </button>

                    <div className="flex items-center space-x-2.5 px-3 py-2 rounded bg-surface-container/50">
                        <div className="w-7 h-7 rounded bg-surface-container-high text-on-surface flex items-center justify-center text-xs font-semibold">
                            {user.name ? user.name.charAt(0).toUpperCase() : 'F'}
                        </div>
                        <div className="flex flex-col text-left overflow-hidden">
                            <span className="text-xs font-medium text-on-surface truncate">{user.name || 'Faculty member'}</span>
                            <span className="text-[10px] text-on-surface-variant truncate">Investigator</span>
                        </div>
                    </div>

                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center space-x-2.5 px-3 py-1.5 rounded text-xs font-medium text-on-surface-variant hover:text-error hover:bg-error-container/20 transition-colors"
                    >
                        <LogOut className="w-4 h-4" strokeWidth={1.5} />
                        <span>Sign out</span>
                    </button>
                </div>
            </aside>

            {/* Main Fluid Content Stage */}
            <main className="flex-1 bg-surface overflow-auto relative print:h-auto print:overflow-visible print:block">
                {children}
            </main>
        </div>
    );
}

