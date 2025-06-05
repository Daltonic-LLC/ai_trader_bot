import React from 'react';

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

    // Parse bullet points and trade details
    const bulletPoints: string[] = [];
    const tradeDetails: string[] = [];
    let inTradeDetails = false;

    for (let i = 1; i < lines.length; i++) {
        const trimmedLine = lines[i].trim(); // Remove leading and trailing spaces
        if (trimmedLine.startsWith('Trade Details:')) {
            inTradeDetails = true;
            continue;
        }
        if (inTradeDetails) {
            tradeDetails.push(lines[i]); // Keep original line to preserve formatting
        } else if (trimmedLine.startsWith('- ')) {
            bulletPoints.push(trimmedLine.substring(2)); // Remove "- " from trimmed line
        }
    }

    // Parse bullet points into key-value pairs
    const parsedBulletPoints = bulletPoints.map(bp => {
        const [key, value] = bp.split(': ', 2);
        return { key, value };
    });

    return (
        <div className="p-5 bg-crypto-gray rounded-xl shadow-lg border border-crypto-blue/30
        hover:border-crypto-blue transition-all relative w-full">
            <div className='max-h-72 overflow-y-auto'>

                {/* Header with coin name */}
                <div className="flex justify-between items-center bg-gradient-to-r from-crypto-blue to-crypto-green text-white py-4 rounded-t-xl">
                    <h2 className="text-xl font-semibold">{`${coinName} Trade Report`}</h2>
                </div>

                {/* Bullet points section */}
                <div className="mt-4 space-y-3">
                    <ul className="space-y-2">
                        {parsedBulletPoints.map(({ key, value }, index) => (
                            <li key={index} className="flex justify-between items-center text-gray-300">
                                <span>{key}</span>
                                <span className="font-medium text-white">{value}</span>
                            </li>
                        ))}
                    </ul>
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
                    {executionLog?.last_execution
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