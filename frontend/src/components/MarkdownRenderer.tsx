import React, { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import mermaid from 'mermaid';
import 'highlight.js/styles/github-dark.css';

mermaid.initialize({
    startOnLoad: true,
    theme: 'default',
    securityLevel: 'loose',
    fontFamily: 'Inter, sans-serif'
});

interface MermaidProps {
    chart: string;
}

const MermaidChart: React.FC<MermaidProps> = ({ chart }) => {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!ref.current || !chart.trim()) return;

        const renderDiagram = async () => {
            try {
                mermaid.contentLoaded();
                const id = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
                // Use a try-catch on the promise to prevent streaming crashes during partial syntax
                const result = await mermaid.render(id, chart);
                if (ref.current) {
                    ref.current.innerHTML = result.svg;
                }
            } catch (err) {
                // Ignore syntax errors while the LLM is still streaming the code block
                console.debug("Mermaid syntax incomplete/streaming:", err);
            }
        };

        renderDiagram();
    }, [chart]);

    return <div key={chart} ref={ref} className="mermaid-chart-container" />;
};

interface MarkdownRendererProps {
    content: string;
}

const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content }) => {
    return (
        <div className="markdown-content">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                    table: ({ node: _, ...props }) => (
                        <div className="table-container">
                            <table {...props} />
                        </div>
                    ),
                    code: ({ node: _1, inline, className, children, ...props }: any) => {
                        const match = /language-mermaid/.exec(className || '');
                        const value = String(children).replace(/\n$/, '');

                        if (!inline && match) {
                            return <MermaidChart chart={value} />;
                        }

                        return (
                            <code className={className} {...props}>
                                {children}
                            </code>
                        );
                    },
                }}
            >
                {content}
            </ReactMarkdown>
        </div>
    );
};

export default MarkdownRenderer;
