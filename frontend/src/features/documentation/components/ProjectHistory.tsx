import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Download, Loader2, CheckCircle2 } from 'lucide-react';
import { documentationService } from '../../../services/documentationService';
import type { ProjectHistoryItem } from '../../../services/documentationService';

export const ProjectHistory: React.FC = () => {
    const [projects, setProjects] = useState<ProjectHistoryItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [downloadingId, setDownloadingId] = useState<number | null>(null);
    const [error, setError] = useState('');

    const fetchHistory = async () => {
        try {
            setIsLoading(true);
            const data = await documentationService.getHistory();
            setProjects(data);
        } catch (err) {
            console.error("Failed to fetch history:", err);
            setError("Failed to load project history.");
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, []);

    const handleDownload = async (project: ProjectHistoryItem) => {
        if (project.status !== 'completed') return;
        try {
            setDownloadingId(project.id);
            const blob = await documentationService.downloadHistoryDocx(project.id);

            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            // Sanitize filename similar to backend
            const safeTitle = project.title.replace(/[^a-zA-Z0-9.\-_ ]/g, '').trim() || 'document';
            a.download = `${safeTitle}.docx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (err) {
            console.error("Failed to download DOCX:", err);
            alert("Failed to download document. Please try again.");
        } finally {
            setDownloadingId(null);
        }
    };

    if (isLoading) {
        return (
            <div className="flex justify-center items-center h-64">
                <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
            </div>
        );
    }

    if (error) {
        return <div className="text-red-500 text-center p-4">{error}</div>;
    }

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    Generation History
                </h2>
                <Button variant="outline" onClick={fetchHistory} size="sm">
                    Refresh
                </Button>
            </div>

            {projects.length === 0 ? (
                <Card className="bg-slate-800/50 border-slate-700">
                    <CardContent className="h-48 flex items-center justify-center text-slate-400">
                        No past projects found. Go generate some documents!
                    </CardContent>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {projects.map((project) => (
                        <Card key={project.id} className="bg-slate-800/50 border-slate-700 hover:border-blue-500/50 transition-colors duration-300">
                            <CardHeader>
                                <CardTitle className="text-lg line-clamp-1 text-slate-100" title={project.title}>
                                    {project.title}
                                </CardTitle>
                                <CardDescription className="text-sm">
                                    {new Date(project.created_at).toLocaleDateString()} at {new Date(project.created_at).toLocaleTimeString()}
                                </CardDescription>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-slate-400 text-sm line-clamp-3">
                                    {project.description || "No description provided."}
                                </p>

                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-300 bg-slate-700/50 px-2 py-1 rounded">
                                        {project.page_count} Pages
                                    </span>

                                    <span className={`flex items-center gap-1 font-medium ${project.status === 'completed' ? 'text-green-400' : 'text-amber-400'
                                        }`}>
                                        {project.status === 'completed' ? (
                                            <CheckCircle2 className="w-4 h-4" />
                                        ) : (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        )}
                                        <span className="capitalize">{project.status}</span>
                                    </span>
                                </div>

                                <Button
                                    className="w-full mt-4 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500"
                                    disabled={project.status !== 'completed' || downloadingId === project.id}
                                    onClick={() => handleDownload(project)}
                                >
                                    {downloadingId === project.id ? (
                                        <>
                                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                            Downloading...
                                        </>
                                    ) : (
                                        <>
                                            <Download className="w-4 h-4 mr-2" />
                                            Download DOCX
                                        </>
                                    )}
                                </Button>
                            </CardContent>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
};
