import React from 'react';
import { MdCopyAll } from "react-icons/md";

interface TradeReportCardProps {
    report: string | null;
    executionLog?: {
        job_name: string;
        last_execution: string;
        next_execution: string;
    } | null;
}

const RecentTradeReportCard: React.FC<TradeReportCardProps> = ({ report, executionLog }) => {
    // Handle case where no report is provided
    if (!report) {
        return (
            <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/20 text-gray-400 text-center">
                No trade report available
            </div>
        );
    }

    // Split the report into lines and filter out empty ones
    const lines = report.split('\n').filter(line => line.trim() !== '');
    if (lines.length === 0) {
        return (
            <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/20 text-gray-400 text-center">
                No trade report available
            </div>
        );
    }

    // Extract coin name from the first line
    const coinName = lines[0].split('Report for ')[1].replace(':', '');

    // Parse the report data
    const reportData: { [key: string]: string } = {};
    const tradeDetails: string[] = [];
    let inTradeDetails = false;

    for (let i = 1; i < lines.length; i++) {
        const line = lines[i].trim();

        if (line.startsWith('Trade Details:')) {
            inTradeDetails = true;
            continue;
        }

        if (inTradeDetails) {
            tradeDetails.push(lines[i]);
        } else {
            // Parse key-value pairs (handle both "Key: Value" and separate line formats)
            const nextLine = i < lines.length - 1 ? lines[i + 1].trim() : '';

            // Check if current line is a key and next line is its value
            if (!line.includes(':') && nextLine && !nextLine.includes(':') && !nextLine.startsWith('Trade Details:')) {
                reportData[line] = nextLine;
                i++; // Skip the next line since we've processed it as a value
            } else if (line.includes(':')) {
                const [key, value] = line.split(':', 2);
                reportData[key.trim()] = value.trim();
            }
        }
    }



    const copyTradeReport = () => {
        // Copy the entire original report with execution log info
        const reportData = {
            report: report,
            executionLog: executionLog
        };
        navigator.clipboard.writeText(JSON.stringify(reportData, null, 2));
    };

    return (
        <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/30
        hover:border-crypto-blue transition-all relative w-full">
            <div className='max-h-72 overflow-y-auto'>

                {/* Header with coin name */}
                <div className="flex justify-between items-center bg-gradient-to-r from-crypto-blue to-crypto-green text-white rounded-t-xl">
                    <h2 className="text-xl font-semibold">{`${coinName} Trade Report`}</h2>

                    <button
                        type="button"
                        className="p-2 rounded hover:bg-white/10 transition cursor-pointer"
                        title="Copy trade report to clipboard"
                        onClick={copyTradeReport}
                    >
                        <MdCopyAll className="w-5 h-5" />
                    </button>
                </div>

                {/* Report data section */}
                <div className="mt-4 space-y-3">
                    {Object.entries(reportData).map(([key, value]) => {
                        if (!value) return null;

                        return (
                            <div key={key} className="flex justify-between items-center text-gray-300">
                                <span>{key}</span>
                                <span className={`font-medium ${key.toLowerCase().includes('recommendation')
                                    ? value.toUpperCase() === 'BUY'
                                        ? 'text-crypto-green'
                                        : value.toUpperCase() === 'SELL'
                                            ? 'text-red-500'
                                            : 'text-white'
                                    : key.toLowerCase().includes('change') && value.startsWith('-')
                                        ? 'text-red-500'
                                        : key.toLowerCase().includes('change') && !value.startsWith('-')
                                            ? 'text-crypto-green'
                                            : 'text-white'
                                    }`}>
                                    {key.toLowerCase().includes('recommendation') && (
                                        <span className="flex items-center gap-1">
                                            {value.toUpperCase() === 'BUY' ? (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                                                </svg>
                                            ) : value.toUpperCase() === 'SELL' ? (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                                                </svg>
                                            ) : null}
                                            {value}
                                        </span>
                                    )}
                                    {key.toLowerCase().includes('change') && (
                                        <span className="flex items-center gap-1">
                                            {value.startsWith('-') ? (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                                                </svg>
                                            ) : (
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
                                                </svg>
                                            )}
                                            {value}
                                        </span>
                                    )}
                                    {!key.toLowerCase().includes('recommendation') && !key.toLowerCase().includes('change') && value}
                                </span>
                            </div>
                        );
                    })}
                </div>

                {/* Trade details section */}
                {tradeDetails.length > 0 && (
                    <div className="mt-4">
                        <h3 className="text-lg font-medium text-white">Trade Details:</h3>
                        <pre className="text-sm text-gray-300 whitespace-pre-wrap">{tradeDetails.join('\n')}</pre>
                    </div>
                )}

            </div>

            <div className="text-gray-300 text-xs pt-3 mb-1">
                {executionLog?.next_execution ? (<span>
                    Next Execution {'   '}
                    {executionLog?.next_execution
                        ? new Date(executionLog.next_execution).toLocaleString()
                        : 'N/A'}
                </span>) : (<span>
                    Last Executed at {'   '} {executionLog?.last_execution
                        ? new Date(executionLog.last_execution).toLocaleString()
                        : 'N/A'}
                </span>)}
            </div>
            {/* Scroll indicator */}
            <div className="absolute bottom-2 left-1/2 transform -translate-x-1/2 text-gray-400 text-xs pt-3">
                Scroll for more
            </div>
        </div>
    );
};

export default RecentTradeReportCard;