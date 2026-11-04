import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  Search,
  Filter,
  MapPin,
  Clock,
  User,
  Plus,
  RefreshCw,
  ChevronRight,
  ChevronLeft,
  Shield,
  ShieldAlert,
  LogIn,
  SlidersHorizontal,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { getIncidents } from '../services/api';
import { Incident, IncidentCategory, IncidentSeverity, IncidentStatus } from '../types';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

export const IncidentListPage: React.FC = () => {
  const { user, role, token } = useAuth();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Pagination State
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(10);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);

  // Debounce search input
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setCurrentPage(1);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  const fetchIncidents = useCallback(async () => {
    if (!token) {
      setLoading(false);
      setIncidents([]);
      setTotalItems(0);
      setTotalPages(1);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await getIncidents(
        {
          category: selectedCategory || undefined,
          severity: selectedSeverity || undefined,
          status: selectedStatus || undefined,
          search: debouncedSearch.trim() || undefined,
          page: currentPage,
          page_size: pageSize,
        },
        token
      );
      setIncidents(response.items);
      setTotalItems(response.total);
      setTotalPages(response.total_pages);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch incident reports.');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory, selectedSeverity, selectedStatus, debouncedSearch, currentPage, pageSize, token]);

  useEffect(() => {
    fetchIncidents();
  }, [fetchIncidents]);

  const handleCategoryChange = (val: string) => {
    setSelectedCategory(val);
    setCurrentPage(1);
  };

  const handleSeverityChange = (val: string) => {
    setSelectedSeverity(val);
    setCurrentPage(1);
  };

  const handleStatusChange = (val: string) => {
    setSelectedStatus(val);
    setCurrentPage(1);
  };

  const handlePageSizeChange = (val: number) => {
    setPageSize(val);
    setCurrentPage(1);
  };

  const getCategoryIcon = (cat: IncidentCategory) => {
    switch (cat) {
      case 'waterlogging':
        return <Droplets className="w-3.5 h-3.5 text-sky-400" />;
      case 'road_damage':
        return <Construction className="w-3.5 h-3.5 text-amber-400" />;
      case 'electrical_hazard':
        return <Zap className="w-3.5 h-3.5 text-yellow-400" />;
      case 'waste_management':
        return <Trash2 className="w-3.5 h-3.5 text-emerald-400" />;
      case 'extreme_heat':
        return <Flame className="w-3.5 h-3.5 text-rose-400" />;
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="space-y-6 pb-12 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-navy-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Community Incident Registry
            </h1>
            <Badge variant="cyan" dot>
              {totalItems} {totalItems === 1 ? 'RECORD' : 'RECORDS'}
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Browse verified community hazard reports, filter by taxonomy, and inspect severity attribution.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchIncidents}
            disabled={loading || !token}
            className="p-2 rounded-lg bg-navy-800 hover:bg-navy-700 border border-navy-700 text-slate-300 hover:text-brand-cyan transition-all disabled:opacity-50"
            title="Refresh Incidents"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin text-brand-cyan' : ''}`} />
          </button>

          <Link to="/incidents/new">
            <Button size="sm" variant="primary">
              <Plus className="w-4 h-4 mr-1" />
              <span>Report Incident</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* Role-Based Access Scope Indicator */}
      {user ? (
        <div className="p-3.5 rounded-xl bg-navy-900/60 border border-navy-800 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-brand-cyan shrink-0" />
            <span className="text-slate-400">Authenticated Access Scope:</span>
            {role === 'COMMUNITY_USER' ? (
              <span className="text-brand-sky font-medium">
                Community Resident View — Restricted to your permitted submissions
              </span>
            ) : role === 'ANALYST' ? (
              <span className="text-amber-400 font-medium">
                Municipal Analyst Triage View — Full platform incident visibility
              </span>
            ) : (
              <span className="text-rose-400 font-medium">
                Administrative Registry View — Full platform incident visibility
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 font-mono text-[11px]">
            <span className="text-slate-500">Caller:</span>
            <span className="text-slate-300">{user.email}</span>
            <Badge
              variant={
                role === 'ADMIN' ? 'high' : role === 'ANALYST' ? 'medium' : 'cyan'
              }
            >
              {role}
            </Badge>
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-navy-900/80 border border-amber-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20 shrink-0">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <p className="font-bold text-white">Authentication Required for Registry Access</p>
              <p className="text-slate-400 mt-0.5">
                Sign in to view your permitted incident records or report hazards with automatic ownership verification.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Link to="/login">
              <Button size="sm" variant="primary">
                <LogIn className="w-3.5 h-3.5 mr-1" />
                <span>Sign In</span>
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm" variant="secondary">
                <span>Register</span>
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* Filter & Search Toolbar */}
      <div className="glass-panel rounded-xl p-4 border border-navy-800 space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 items-center">
          {/* Search bar */}
          <div className="lg:col-span-4 relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by title, location, or ID..."
              className="w-full pl-9 pr-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan transition-all"
            />
          </div>

          {/* Category Dropdown */}
          <div className="lg:col-span-3">
            <select
              value={selectedCategory}
              onChange={(e) => handleCategoryChange(e.target.value)}
              className="w-full px-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-cyan"
            >
              <option value="">All Categories (5 Types)</option>
              <option value="waterlogging">Waterlogging</option>
              <option value="road_damage">Road Damage</option>
              <option value="electrical_hazard">Electrical Hazard</option>
              <option value="waste_management">Waste Management</option>
              <option value="extreme_heat">Extreme Heat</option>
            </select>
          </div>

          {/* Severity Dropdown */}
          <div className="lg:col-span-2">
            <select
              value={selectedSeverity}
              onChange={(e) => handleSeverityChange(e.target.value)}
              className="w-full px-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-cyan"
            >
              <option value="">All Severities</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
            </select>
          </div>

          {/* Status Dropdown */}
          <div className="lg:col-span-2">
            <select
              value={selectedStatus}
              onChange={(e) => handleStatusChange(e.target.value)}
              className="w-full px-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-cyan"
            >
              <option value="">All Statuses</option>
              <option value="reported">Reported</option>
              <option value="investigating">Investigating</option>
              <option value="mitigating">Mitigating</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>

          {/* Page Size Selector */}
          <div className="lg:col-span-1">
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="w-full px-2 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-brand-cyan"
              title="Items per page"
            >
              <option value={10}>10/p</option>
              <option value={20}>20/p</option>
              <option value={50}>50/p</option>
            </select>
          </div>
        </div>
      </div>

      {/* Incident List Content */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 space-y-3">
          <div className="w-8 h-8 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
          <p className="text-xs font-mono text-slate-400">LOADING INCIDENT REGISTRY...</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-xl bg-rose-950/30 border border-rose-800/40 text-center space-y-2">
          <AlertTriangle className="w-8 h-8 text-rose-400 mx-auto" />
          <p className="text-sm font-semibold text-rose-200">Could not retrieve incidents</p>
          <p className="text-xs text-rose-300/80">{error}</p>
          <Button size="sm" variant="secondary" onClick={fetchIncidents} className="mt-3">
            Retry
          </Button>
        </div>
      ) : !token ? (
        <div className="p-12 glass-panel rounded-xl border border-navy-800 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-navy-900 border border-navy-700 text-slate-400 flex items-center justify-center mx-auto">
            <Shield className="w-6 h-6 text-brand-cyan" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Sign In to View Incidents</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              The NEXUS AI incident registry is protected by role-based access control. Community users only see their permitted records, while municipal leaders access citywide telemetry.
            </p>
          </div>
          <div className="flex items-center justify-center gap-3">
            <Link to="/login">
              <Button size="sm" variant="primary">
                <LogIn className="w-3.5 h-3.5 mr-1" />
                <span>Sign In to Console</span>
              </Button>
            </Link>
            <Link to="/register">
              <Button size="sm" variant="secondary">
                <span>Create Account</span>
              </Button>
            </Link>
          </div>
        </div>
      ) : incidents.length === 0 ? (
        <div className="p-12 glass-panel rounded-xl border border-navy-800 text-center space-y-4">
          <div className="w-12 h-12 rounded-xl bg-navy-900 border border-navy-700 text-slate-400 flex items-center justify-center mx-auto">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">No Incidents Found</h3>
            <p className="text-xs text-slate-400 mt-1">
              {searchTerm || selectedCategory || selectedSeverity || selectedStatus
                ? 'No incident reports match your current search and filter criteria.'
                : 'Zero incidents recorded in your registry view. Submit the first incident report!'}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3">
            {(searchTerm || selectedCategory || selectedSeverity || selectedStatus) && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  setSearchTerm('');
                  setSelectedCategory('');
                  setSelectedSeverity('');
                  setSelectedStatus('');
                  setCurrentPage(1);
                }}
              >
                Clear Filters
              </Button>
            )}
            <Link to="/incidents/new">
              <Button size="sm" variant="primary">
                <Plus className="w-3.5 h-3.5 mr-1" />
                <span>Report Incident</span>
              </Button>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-1 gap-4">
            {incidents.map((incident) => (
              <Link
                key={incident.id}
                to={`/incidents/${incident.id}`}
                className="glass-panel glass-panel-hover rounded-xl p-5 border border-navy-800 block group transition-all"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-navy-800/60">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg bg-navy-900 border border-navy-700">
                      {getCategoryIcon(incident.category)}
                    </div>
                    <div>
                      <span className="font-mono text-xs font-bold text-brand-cyan">
                        {incident.id}
                      </span>
                      <span className="text-slate-500 mx-2">·</span>
                      <span className="text-xs font-semibold text-slate-300 capitalize">
                        {incident.category.replace('_', ' ')}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        incident.severity === 'HIGH'
                          ? 'high'
                          : incident.severity === 'MEDIUM'
                          ? 'medium'
                          : 'low'
                      }
                      dot
                    >
                      {incident.severity}
                    </Badge>

                    <Badge variant="neutral">
                      {incident.status}
                    </Badge>
                  </div>
                </div>

                <div className="pt-3">
                  <h3 className="text-base font-bold text-white group-hover:text-brand-cyan transition-colors">
                    {incident.title}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {incident.description}
                  </p>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-4 mt-4 pt-3 border-t border-navy-800/40 text-xs text-slate-400 font-mono">
                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1.5">
                      <MapPin className="w-3.5 h-3.5 text-slate-500" />
                      <span className="text-slate-300 truncate max-w-xs">{incident.location}</span>
                    </span>

                    {incident.latitude && incident.longitude && (
                      <span className="text-[11px] text-brand-sky hidden md:inline">
                        [{incident.latitude.toFixed(4)}, {incident.longitude.toFixed(4)}]
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-4">
                    <span className="flex items-center gap-1 text-[11px]">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{formatDate(incident.created_at)}</span>
                    </span>

                    <span className="flex items-center gap-1 text-[11px] text-slate-400">
                      <User className="w-3 h-3 text-slate-500" />
                      <span>{incident.reporter_email.split('@')[0]}</span>
                    </span>

                    <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-brand-cyan group-hover:translate-x-1 transition-all" />
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t border-navy-800 text-xs font-mono">
              <span className="text-slate-400">
                Showing{' '}
                <span className="text-white font-semibold">
                  {(currentPage - 1) * pageSize + 1}
                </span>{' '}
                to{' '}
                <span className="text-white font-semibold">
                  {Math.min(currentPage * pageSize, totalItems)}
                </span>{' '}
                of <span className="text-brand-cyan font-semibold">{totalItems}</span> reports
              </span>

              <div className="flex items-center gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage <= 1}
                  className="px-2.5 py-1.5"
                >
                  <ChevronLeft className="w-3.5 h-3.5 mr-1" />
                  <span>Prev</span>
                </Button>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1)
                  .map((p, idx, arr) => {
                    const prev = arr[idx - 1];
                    const showEllipsis = prev && p - prev > 1;
                    return (
                      <React.Fragment key={p}>
                        {showEllipsis && <span className="text-slate-600 px-1">...</span>}
                        <button
                          onClick={() => setCurrentPage(p)}
                          className={`w-7 h-7 rounded text-xs transition-colors ${
                            p === currentPage
                              ? 'bg-brand-cyan text-navy-950 font-bold'
                              : 'bg-navy-900 text-slate-400 hover:text-white hover:bg-navy-800'
                          }`}
                        >
                          {p}
                        </button>
                      </React.Fragment>
                    );
                  })}

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage >= totalPages}
                  className="px-2.5 py-1.5"
                >
                  <span>Next</span>
                  <ChevronRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
