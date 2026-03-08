import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../../../components/ui/Card';
import { Progress } from '../../../components/ui/Progress';
import { Loader2, CheckCircle2, Circle, FileStack, Sparkles } from 'lucide-react';

interface GenerationStatusProps {
    index: string[];
    currentSectionIndex: number;
    isComplete: boolean;
}

export const GenerationStatus: React.FC<GenerationStatusProps> = ({ index, currentSectionIndex, isComplete }) => {
    const progress = index.length > 0 ? ((currentSectionIndex + 1) / index.length) * 100 : 0;

    return (
        <Card className="max-w-xl mx-auto mt-20">
            <CardHeader>
                <CardTitle className="flex items-center gap-2">
                    <FileStack className="text-primary" />
                    Documentation Forge
                </CardTitle>
                <CardDescription>
                    {isComplete ? 'Forge successful. Documentation finalized.' : 'Transmuting data into structured technical prose...'}
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
                <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                        <span>Overall Progress</span>
                        <span className="font-mono">{Math.round(progress)}%</span>
                    </div>
                    <Progress value={progress} />
                </div>

                <div className="space-y-4 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {index.map((item, i) => {
                        const isFinished = i < currentSectionIndex || isComplete;
                        const isCurrent = i === currentSectionIndex && !isComplete;

                        return (
                            <div
                                key={i}
                                className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${isCurrent ? 'border-primary bg-primary/5 shadow-sm' : 'border-transparent opacity-60'
                                    }`}
                            >
                                {isFinished ? (
                                    <CheckCircle2 className="text-green-500 shrink-0" size={18} />
                                ) : isCurrent ? (
                                    <Loader2 className="text-primary animate-spin shrink-0" size={18} />
                                ) : (
                                    <Circle className="text-muted-foreground shrink-0" size={18} />
                                )}
                                <span className={`text-sm ${isCurrent ? 'font-bold' : ''}`}>
                                    {item}
                                </span>
                                {isCurrent && (
                                    <Sparkles className="ml-auto text-primary animate-pulse" size={14} />
                                )}
                            </div>
                        );
                    })}
                </div>
            </CardContent>
            <CardFooter className="bg-muted/50 p-4 mt-4 flex justify-between items-center text-xs text-muted-foreground">
                <span>Master Documentation System v1.0.4</span>
                <span className="flex items-center gap-1">
                    <Circle size={8} className="fill-green-500 text-green-500" />
                    Neural Link Active
                </span>
            </CardFooter>
        </Card>
    );
};
