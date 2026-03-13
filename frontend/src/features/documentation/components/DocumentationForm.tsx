import React, { useState } from 'react';
import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Textarea } from '../../../components/ui/Textarea';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../../components/ui/Card';
import { Plus, X, Wand2, FileText, ListOrdered } from 'lucide-react';
import type { ProjectData } from '../../../services/documentationService';

type OptionalOutputKey = 'include_code' | 'include_flowcharts' | 'include_graphs' | 'include_charts';

interface DocumentationFormProps {
    onSubmit: (data: ProjectData) => void;
    isGenerating: boolean;
}

export const DocumentationForm: React.FC<DocumentationFormProps> = ({ onSubmit, isGenerating }) => {
    const [data, setData] = useState<ProjectData>({
        title: '',
        page_count: 50,
        description: '',
        custom_index: [],
        theme_color: '#1F4E79',
        include_code: true,
        include_flowcharts: true,
        include_graphs: true,
        include_charts: true,
    });
    const optionalOutputs: { key: OptionalOutputKey; label: string }[] = [
        { key: 'include_code', label: 'Code snippets' },
        { key: 'include_flowcharts', label: 'Flowcharts' },
        { key: 'include_graphs', label: 'Graphs' },
        { key: 'include_charts', label: 'Charts' },
    ];

    const [newItem, setNewItem] = useState('');

    const handleAddItem = () => {
        if (newItem.trim()) {
            setData(prev => ({
                ...prev,
                custom_index: [...prev.custom_index, newItem.trim()]
            }));
            setNewItem('');
        }
    };

    const handleRemoveItem = (index: number) => {
        setData(prev => ({
            ...prev,
            custom_index: prev.custom_index.filter((_, i) => i !== index)
        }));
    };

    return (
        <div className="max-w-4xl mx-auto py-10 px-4 space-y-8">
            <div className="space-y-2">
                <h1 className="text-3xl font-bold tracking-tight">Documentation Forge</h1>
                <p className="text-muted-foreground">
                    Enter your project details to generate comprehensive master documentation.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <Card className="md:col-span-2">
                    <CardHeader>
                        <CardTitle>Project Details</CardTitle>
                        <CardDescription>Basic information about your technical project.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Project Title</label>
                            <Input
                                placeholder="e.g. Enterprise Cloud Nexus"
                                value={data.title}
                                onChange={e => setData(prev => ({ ...prev, title: e.target.value }))}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Page Target</label>
                            <Input
                                type="number"
                                value={data.page_count}
                                onChange={e => setData(prev => ({ ...prev, page_count: parseInt(e.target.value) }))}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Document Accent</label>
                            <div className="flex items-center gap-3">
                                <Input
                                    type="color"
                                    value={data.theme_color}
                                    onChange={e => setData(prev => ({ ...prev, theme_color: e.target.value.toUpperCase() }))}
                                    className="h-11 w-16 p-1"
                                />
                                <div className="text-sm text-muted-foreground">
                                    {data.theme_color.toUpperCase()} for headings, tables, cover accents, and callouts.
                                </div>
                            </div>
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Description & Architecture Brief</label>
                            <Textarea
                                className="min-h-[200px]"
                                placeholder="Describe features, tech stack, data flow..."
                                value={data.description}
                                onChange={e => setData(prev => ({ ...prev, description: e.target.value }))}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Optional Outputs</label>
                            <div className="grid grid-cols-2 gap-3">
                                {optionalOutputs.map(option => (
                                    <label key={option.key} className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm font-medium">
                                        <input
                                            type="checkbox"
                                            checked={data[option.key]}
                                            onChange={e => setData(prev => ({ ...prev, [option.key]: e.target.checked }))}
                                        />
                                        <span>{option.label}</span>
                                    </label>
                                ))}
                            </div>
                            <div className="text-xs text-muted-foreground">
                                Disabled items will not be planned or generated.
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <ListOrdered size={20} />
                            Manual Index
                        </CardTitle>
                        <CardDescription>Optional: Define specific sections.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex gap-2">
                            <Input
                                placeholder="Add section..."
                                value={newItem}
                                onChange={e => setNewItem(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleAddItem()}
                            />
                            <Button size="icon" variant="outline" onClick={handleAddItem}>
                                <Plus size={16} />
                            </Button>
                        </div>
                        <div className="space-y-2 max-h-[300px] overflow-y-auto">
                            {data.custom_index.length === 0 ? (
                                <div className="text-center py-8 border-2 border-dashed rounded-lg text-muted-foreground text-sm">
                                    No custom sections.<br />AI will auto-map the index.
                                </div>
                            ) : (
                                data.custom_index.map((item, i) => (
                                    <div key={i} className="flex items-center justify-between p-2 bg-muted rounded-md group">
                                        <span className="text-sm truncate pr-2">{item}</span>
                                        <button
                                            onClick={() => handleRemoveItem(i)}
                                            className="text-muted-foreground hover:text-destructive"
                                        >
                                            <X size={14} />
                                        </button>
                                    </div>
                                ))
                            )}
                        </div>
                    </CardContent>
                    <CardFooter className="flex flex-col gap-4">
                        <Button
                            className="w-full"
                            size="lg"
                            disabled={!data.title || !data.description || isGenerating}
                            onClick={() => onSubmit(data)}
                        >
                            {isGenerating ? <Wand2 className="mr-2 animate-spin" /> : <FileText className="mr-2" />}
                            {isGenerating ? 'Generating...' : 'Start Forge'}
                        </Button>
                        <p className="text-[10px] text-center text-muted-foreground uppercase tracking-widest">
                            Powered by DeepSeek V3.2
                        </p>
                    </CardFooter>
                </Card>
            </div>
        </div>
    );
};
