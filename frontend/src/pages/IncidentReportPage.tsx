import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  Droplets,
  Construction,
  Zap,
  Trash2,
  Flame,
  MapPin,
  Upload,
  CheckCircle2,
  AlertCircle,
  X,
  Compass,
  ArrowRight,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { createIncident } from '../services/api';
import { storage, isStorageConfigured, ref, uploadBytes, getDownloadURL } from '../services/firebase';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { IncidentCategory, IncidentSeverity, Incident } from '../types';

export const IncidentReportPage: React.FC = () => {
  const { user, token } = useAuth();
  const navigate = useNavigate();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState<IncidentCategory>('waterlogging');
  const [severity, setSeverity] = useState<IncidentSeverity>('MEDIUM');
  const [location, setLocation] = useState('');
  const [latitude, setLatitude] = useState<string>('');
  const [longitude, setLongitude] = useState<string>('');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isUploadingImage, setIsUploadingImage] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdIncident, setCreatedIncident] = useState<Incident | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const categories = [
    {
      id: 'waterlogging' as IncidentCategory,
      label: 'Waterlogging',
      icon: Droplets,
      color: 'border-cyan-500/40 text-cyan-400 bg-cyan-950/20',
      activeColor: 'border-brand-cyan bg-cyan-950/60 shadow-glow-cyan',
    },
    {
      id: 'road_damage' as IncidentCategory,
      label: 'Road Damage',
      icon: Construction,
      color: 'border-amber-500/40 text-amber-400 bg-amber-950/20',
      activeColor: 'border-amber-400 bg-amber-950/60 shadow-[0_0_15px_-3px_rgba(251,191,36,0.3)]',
    },
    {
      id: 'electrical_hazard' as IncidentCategory,
      label: 'Electrical Hazard',
      icon: Zap,
      color: 'border-yellow-500/40 text-yellow-400 bg-yellow-950/20',
      activeColor: 'border-yellow-400 bg-yellow-950/60 shadow-[0_0_15px_-3px_rgba(250,204,21,0.3)]',
    },
    {
      id: 'waste_management' as IncidentCategory,
      label: 'Waste Management',
      icon: Trash2,
      color: 'border-emerald-500/40 text-emerald-400 bg-emerald-950/20',
      activeColor: 'border-emerald-400 bg-emerald-950/60 shadow-[0_0_15px_-3px_rgba(52,211,153,0.3)]',
    },
    {
      id: 'extreme_heat' as IncidentCategory,
      label: 'Extreme Heat',
      icon: Flame,
      color: 'border-rose-500/40 text-rose-400 bg-rose-950/20',
      activeColor: 'border-rose-500 bg-rose-950/60 shadow-[0_0_15px_-3px_rgba(244,63,94,0.3)]',
    },
  ];

  const handleGetLocation = () => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      return;
    }
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLatitude(pos.coords.latitude.toFixed(6));
        setLongitude(pos.coords.longitude.toFixed(6));
        setIsLocating(false);
      },
      (err) => {
        setError(`Could not retrieve location: ${err.message}`);
        setIsLocating(false);
      },
      { timeout: 8000 }
    );
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!isStorageConfigured) {
      setError('Firebase Storage is not configured in this environment. Field image uploads are currently unavailable.');
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError('Image file must be under 5MB.');
      return;
    }

    setIsUploadingImage(true);
    setError(null);
    try {
      const sanitizedName = file.name.replace(/[^a-zA-Z0-9.-]/g, '_');
      const storagePath = `incidents/${Date.now()}_${sanitizedName}`;
      const imageRef = ref(storage, storagePath);
      await uploadBytes(imageRef, file);
      const downloadUrl = await getDownloadURL(imageRef);
      setImageUrl(downloadUrl);
      setImagePreview(downloadUrl);
    } catch (uploadErr: unknown) {
      console.warn('Storage upload error, falling back to local preview:', uploadErr);
      const reader = new FileReader();
      reader.onloadend = () => {
        const dataUrl = reader.result as string;
        setImageUrl(dataUrl);
        setImagePreview(dataUrl);
      };
      reader.readAsDataURL(file);
    } finally {
      setIsUploadingImage(false);
    }
  };

  const handleRemoveImage = () => {
    setImageUrl(null);
    setImagePreview(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim() || title.length < 3) {
      setError('Please provide a title of at least 3 characters.');
      return;
    }
    if (!description.trim() || description.length < 10) {
      setError('Please provide a detailed description of at least 10 characters.');
      return;
    }
    if (!location.trim() || location.length < 3) {
      setError('Please enter a location or landmark.');
      return;
    }

    if (!token) {
      setError('You must be signed in to submit an incident report.');
      return;
    }

    setIsSubmitting(true);
    try {
      const parsedLat = latitude ? parseFloat(latitude) : null;
      const parsedLng = longitude ? parseFloat(longitude) : null;

      const incident = await createIncident(
        {
          title: title.trim(),
          description: description.trim(),
          category,
          severity,
          location: location.trim(),
          latitude: parsedLat,
          longitude: parsedLng,
          image_url: imageUrl,
        },
        token
      );

      setCreatedIncident(incident);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to submit incident report.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (createdIncident) {
    return (
      <div className="max-w-2xl mx-auto py-8">
        <div className="glass-panel rounded-xl p-8 border border-emerald-500/30 text-center space-y-5">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto shadow-[0_0_20px_-3px_rgba(16,185,129,0.3)]">
            <CheckCircle2 className="w-8 h-8" />
          </div>

          <div className="space-y-2">
            <Badge variant="low" dot>
              INCIDENT REGISTERED
            </Badge>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Report Ingested Successfully
            </h2>
            <p className="text-xs text-slate-400 font-mono">
              Server Incident ID:{' '}
              <span className="text-brand-cyan font-bold">{createdIncident.id}</span>
            </p>
          </div>

          <div className="p-4 rounded-lg bg-navy-900/80 border border-navy-800 text-left text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Category:</span>
              <span className="text-white font-medium capitalize">{createdIncident.category}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Severity:</span>
              <span className="text-amber-400 font-semibold">{createdIncident.severity}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Location:</span>
              <span className="text-slate-200">{createdIncident.location}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Timestamp:</span>
              <span className="text-slate-400 font-mono">{createdIncident.created_at}</span>
            </div>
          </div>

          <div className="flex items-center justify-center gap-3 pt-2">
            <Link to={`/incidents/${createdIncident.id}`}>
              <Button variant="primary" size="sm">
                <span>View Incident Detail</span>
                <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            </Link>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setCreatedIncident(null);
                setTitle('');
                setDescription('');
                setLocation('');
                setLatitude('');
                setLongitude('');
                setImageUrl(null);
                setImagePreview(null);
              }}
            >
              Submit Another Report
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-8 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-navy-800">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Submit Community Incident Report
            </h1>
            <Badge variant="cyan" dot>
              INGESTION
            </Badge>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Multimodal hazard submission with automated TF-IDF categorization and multi-factor risk routing.
          </p>
        </div>

        <Link to="/incidents">
          <Button variant="secondary" size="sm">
            View All Reports
          </Button>
        </Link>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/40 flex items-start gap-3 text-xs text-rose-300">
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-rose-200">Submission Blocked</p>
            <p className="mt-0.5 text-rose-300/90">{error}</p>
          </div>
        </div>
      )}

      {/* Main Reporting Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Category Selection */}
        <div className="glass-panel rounded-xl p-5 border border-navy-800 space-y-3">
          <label className="block text-xs font-mono uppercase tracking-wider text-slate-300">
            1. Select Incident Category *
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {categories.map((cat) => {
              const Icon = cat.icon;
              const isSelected = category === cat.id;
              return (
                <button
                  key={cat.id}
                  type="button"
                  onClick={() => setCategory(cat.id)}
                  className={`p-3 rounded-lg border text-left transition-all cursor-pointer flex flex-col justify-between h-24 ${
                    isSelected ? cat.activeColor : 'border-navy-700 bg-navy-900/50 hover:bg-navy-800 text-slate-400'
                  }`}
                >
                  <Icon className={`w-5 h-5 ${isSelected ? 'text-white' : 'text-slate-400'}`} />
                  <div>
                    <span className={`text-xs font-semibold block ${isSelected ? 'text-white' : 'text-slate-300'}`}>
                      {cat.label}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Severity Selection */}
        <div className="glass-panel rounded-xl p-5 border border-navy-800 space-y-3">
          <label className="block text-xs font-mono uppercase tracking-wider text-slate-300">
            2. Initial Severity Level *
          </label>
          <div className="grid grid-cols-3 gap-3">
            <button
              type="button"
              onClick={() => setSeverity('LOW')}
              className={`p-3 rounded-lg border text-center transition-all cursor-pointer ${
                severity === 'LOW'
                  ? 'border-emerald-500 bg-emerald-950/50 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
                  : 'border-navy-700 bg-navy-900/50 text-slate-400 hover:bg-navy-800'
              }`}
            >
              <div className="font-bold text-xs uppercase">LOW</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Monitoring</div>
            </button>

            <button
              type="button"
              onClick={() => setSeverity('MEDIUM')}
              className={`p-3 rounded-lg border text-center transition-all cursor-pointer ${
                severity === 'MEDIUM'
                  ? 'border-amber-500 bg-amber-950/50 text-amber-400 shadow-[0_0_12px_rgba(245,158,11,0.3)]'
                  : 'border-navy-700 bg-navy-900/50 text-slate-400 hover:bg-navy-800'
              }`}
            >
              <div className="font-bold text-xs uppercase">MEDIUM</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Elevated Risk</div>
            </button>

            <button
              type="button"
              onClick={() => setSeverity('HIGH')}
              className={`p-3 rounded-lg border text-center transition-all cursor-pointer ${
                severity === 'HIGH'
                  ? 'border-rose-500 bg-rose-950/50 text-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.3)]'
                  : 'border-navy-700 bg-navy-900/50 text-slate-400 hover:bg-navy-800'
              }`}
            >
              <div className="font-bold text-xs uppercase">HIGH</div>
              <div className="text-[10px] text-slate-400 mt-0.5">Critical Emergency</div>
            </button>
          </div>
        </div>

        {/* Title & Description */}
        <div className="glass-panel rounded-xl p-5 border border-navy-800 space-y-4">
          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300">
                3. Incident Title *
              </label>
              <span className="text-[10px] font-mono text-slate-500">{title.length}/200</span>
            </div>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Submerged Underpass Roadway Near Sector 4 Junction"
              maxLength={200}
              className="w-full px-3.5 py-2.5 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
              required
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1.5">
              <label className="block text-xs font-mono uppercase tracking-wider text-slate-300">
                4. Hazard Description & Context *
              </label>
              <span className="text-[10px] font-mono text-slate-500">{description.length}/2500</span>
            </div>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe physical hazard depth, asset exposure, nearby schools/transit hubs, and immediate risks to residents..."
              rows={4}
              maxLength={2500}
              className="w-full px-3.5 py-2.5 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
              required
            />
          </div>
        </div>

        {/* Geolocation Details */}
        <div className="glass-panel rounded-xl p-5 border border-navy-800 space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-300 mb-1.5">
              5. Address, Landmark, or Intersection *
            </label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Metro Pillar 142, Outer Ring Road"
                className="w-full pl-9 pr-3 py-2.5 bg-navy-900/80 border border-navy-700/80 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                required
              />
            </div>
          </div>

          <div className="pt-2 border-t border-navy-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">
                Geographic Coordinates (Optional)
              </span>
              <button
                type="button"
                onClick={handleGetLocation}
                disabled={isLocating}
                className="text-xs text-brand-cyan hover:underline font-mono inline-flex items-center gap-1 cursor-pointer"
              >
                <Compass className={`w-3.5 h-3.5 ${isLocating ? 'animate-spin' : ''}`} />
                <span>{isLocating ? 'Acquiring GPS...' : 'Use Current Device GPS'}</span>
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                  placeholder="Latitude (e.g. 28.6139)"
                  className="w-full px-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                />
              </div>
              <div>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                  placeholder="Longitude (e.g. 77.2090)"
                  className="w-full px-3 py-2 bg-navy-900/80 border border-navy-700/80 rounded-lg text-xs font-mono text-white placeholder-slate-500 focus:outline-none focus:border-brand-cyan focus:ring-1 focus:ring-brand-cyan transition-all"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Media / Image Attachment */}
        <div className="glass-panel rounded-xl p-5 border border-navy-800 space-y-3">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-mono uppercase tracking-wider text-slate-300">
              6. Hazard Photo Attachment (Optional)
            </label>
            {!isStorageConfigured && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-950/50 border border-amber-500/30 text-amber-400">
                STORAGE NOT CONFIGURED
              </span>
            )}
          </div>

          {!isStorageConfigured ? (
            <div className="p-4 rounded-lg bg-navy-900/60 border border-amber-500/20 text-xs text-slate-400 space-y-2">
              <div className="flex items-start gap-2 text-amber-300">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <p className="font-semibold">Image Uploads Currently Unavailable</p>
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Firebase Storage is not configured for this environment (storage bucket placeholder in use).
                Incident reporting will proceed cleanly with textual description, category, severity, and GPS coordinates.
              </p>
            </div>
          ) : imagePreview ? (
            <div className="relative inline-block rounded-lg overflow-hidden border border-brand-cyan/40 shadow-glow-cyan">
              <img
                src={imagePreview}
                alt="Hazard attachment"
                className="max-h-56 rounded-lg object-cover"
              />
              <button
                type="button"
                onClick={handleRemoveImage}
                className="absolute top-2 right-2 p-1 rounded-full bg-navy-950/80 text-rose-400 hover:text-white transition-colors"
                title="Remove photo"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="border-2 border-dashed border-navy-700 hover:border-brand-cyan/50 rounded-lg p-6 text-center transition-colors">
              <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
              <label className="cursor-pointer text-xs font-semibold text-brand-cyan hover:underline">
                <span>{isUploadingImage ? 'Uploading to Firebase Storage...' : 'Upload hazard image'}</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageUpload}
                  disabled={isUploadingImage}
                  className="hidden"
                />
              </label>
              <p className="text-[11px] text-slate-500 mt-1">PNG, JPG, or WEBP up to 5MB</p>
            </div>
          )}
        </div>

        {/* Submit Action */}
        <div className="flex items-center justify-between pt-2">
          <Link to="/incidents">
            <Button variant="ghost" size="md">
              Cancel
            </Button>
          </Link>

          <Button type="submit" variant="primary" size="lg" isLoading={isSubmitting}>
            <AlertTriangle className="w-4 h-4 mr-1.5" />
            <span>Submit Incident for AI Intelligence</span>
          </Button>
        </div>
      </form>
    </div>
  );
};
