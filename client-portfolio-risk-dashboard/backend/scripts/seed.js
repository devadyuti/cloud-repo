import { DynamoDBClient } from '@aws-sdk/client-dynamodb';
import { DynamoDBDocumentClient, BatchWriteCommand } from '@aws-sdk/lib-dynamodb';

const client = new DynamoDBClient({ region: 'eu-west-1' });
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = process.env.TABLE_NAME || 'ClientPortfolios-dev';

const clients = [
  {
    PK: 'CLIENT#CLT001',
    SK: 'PROFILE',
    id: 'CLT001',
    name: 'Smith Family Trust',
    portfolioValue: 2450000,
    riskProfile: 'Balanced',
    lastReviewDate: '2026-03-15',
    investmentManager: 'James Richardson'
  },
  {
    PK: 'CLIENT#CLT002',
    SK: 'PROFILE',
    id: 'CLT002',
    name: 'Dr. Sarah Mitchell',
    portfolioValue: 890000,
    riskProfile: 'Growth',
    lastReviewDate: '2026-02-28',
    investmentManager: 'James Richardson'
  },
  {
    PK: 'CLIENT#CLT003',
    SK: 'PROFILE',
    id: 'CLT003',
    name: 'Henderson Charitable Foundation',
    portfolioValue: 5200000,
    riskProfile: 'Conservative',
    lastReviewDate: '2026-04-01',
    investmentManager: 'James Richardson'
  },
  {
    PK: 'CLIENT#CLT004',
    SK: 'PROFILE',
    id: 'CLT004',
    name: 'Mr. & Mrs. Patel',
    portfolioValue: 1750000,
    riskProfile: 'Balanced',
    lastReviewDate: '2026-03-22',
    investmentManager: 'James Richardson'
  },
  {
    PK: 'CLIENT#CLT005',
    SK: 'PROFILE',
    id: 'CLT005',
    name: 'Westbury Pension Scheme',
    portfolioValue: 8900000,
    riskProfile: 'Conservative',
    lastReviewDate: '2026-04-10',
    investmentManager: 'James Richardson'
  }
];

const portfolios = [
  {
    PK: 'CLIENT#CLT001',
    SK: 'PORTFOLIO',
    clientId: 'CLT001',
    allocation: {
      ukEquities: 38,
      internationalEquities: 25,
      fixedIncome: 20,
      alternatives: 10,
      cash: 7
    },
    holdings: [
      { name: 'Shell PLC', sector: 'Energy', value: 245000, weight: 10.0, change1M: 2.3 },
      { name: 'AstraZeneca', sector: 'Healthcare', value: 220500, weight: 9.0, change1M: 1.8 },
      { name: 'HSBC Holdings', sector: 'Financials', value: 196000, weight: 8.0, change1M: -0.5 },
      { name: 'Unilever', sector: 'Consumer Staples', value: 183750, weight: 7.5, change1M: 0.9 },
      { name: 'Microsoft Corp', sector: 'Technology', value: 171500, weight: 7.0, change1M: 3.2 },
      { name: 'iShares Core UK Gilts', sector: 'Fixed Income', value: 147000, weight: 6.0, change1M: 0.3 },
      { name: 'Diageo', sector: 'Consumer Staples', value: 134750, weight: 5.5, change1M: -1.2 },
      { name: 'Rio Tinto', sector: 'Materials', value: 122500, weight: 5.0, change1M: -2.1 },
      { name: 'Legal & General', sector: 'Financials', value: 110250, weight: 4.5, change1M: 1.1 },
      { name: 'Blackrock Global Allocation', sector: 'Alternatives', value: 98000, weight: 4.0, change1M: 0.7 }
    ],
    riskMetrics: {
      volatility: 11.2,
      sharpeRatio: 0.85,
      maxDrawdown: -8.4,
      betaFTSE100: 0.92
    }
  },
  {
    PK: 'CLIENT#CLT002',
    SK: 'PORTFOLIO',
    clientId: 'CLT002',
    allocation: {
      ukEquities: 45,
      internationalEquities: 30,
      fixedIncome: 10,
      alternatives: 12,
      cash: 3
    },
    holdings: [
      { name: 'Tesla Inc', sector: 'Technology', value: 106800, weight: 12.0, change1M: 5.4 },
      { name: 'NVIDIA Corp', sector: 'Technology', value: 97900, weight: 11.0, change1M: 8.2 },
      { name: 'Amazon.com', sector: 'Consumer Discretionary', value: 89000, weight: 10.0, change1M: 3.7 },
      { name: 'ARM Holdings', sector: 'Technology', value: 80100, weight: 9.0, change1M: 6.1 },
      { name: 'Rolls-Royce Holdings', sector: 'Industrials', value: 71200, weight: 8.0, change1M: 4.3 },
      { name: 'Scottish Mortgage IT', sector: 'Investment Trust', value: 62300, weight: 7.0, change1M: 2.9 },
      { name: 'Alphabet Inc', sector: 'Technology', value: 53400, weight: 6.0, change1M: 1.5 },
      { name: 'BAE Systems', sector: 'Defence', value: 48950, weight: 5.5, change1M: 3.8 },
      { name: 'Fundsmith Equity', sector: 'Multi-Asset', value: 44500, weight: 5.0, change1M: 1.2 },
      { name: 'Bitcoin ETP', sector: 'Alternatives', value: 35600, weight: 4.0, change1M: -4.5 }
    ],
    riskMetrics: {
      volatility: 18.5,
      sharpeRatio: 1.12,
      maxDrawdown: -15.3,
      betaFTSE100: 1.25
    }
  },
  {
    PK: 'CLIENT#CLT003',
    SK: 'PORTFOLIO',
    clientId: 'CLT003',
    allocation: {
      ukEquities: 15,
      internationalEquities: 10,
      fixedIncome: 45,
      alternatives: 15,
      cash: 15
    },
    holdings: [
      { name: 'iShares Core UK Gilts', sector: 'Fixed Income', value: 780000, weight: 15.0, change1M: 0.4 },
      { name: 'Vanguard UK Govt Bond', sector: 'Fixed Income', value: 624000, weight: 12.0, change1M: 0.2 },
      { name: 'M&G Corporate Bond', sector: 'Fixed Income', value: 520000, weight: 10.0, change1M: 0.6 },
      { name: 'National Grid', sector: 'Utilities', value: 416000, weight: 8.0, change1M: 0.8 },
      { name: 'SSE PLC', sector: 'Utilities', value: 364000, weight: 7.0, change1M: 1.1 },
      { name: 'Tritax Big Box REIT', sector: 'Real Estate', value: 312000, weight: 6.0, change1M: -0.3 },
      { name: 'British Land', sector: 'Real Estate', value: 260000, weight: 5.0, change1M: -0.8 },
      { name: 'Greencoat UK Wind', sector: 'Renewables', value: 234000, weight: 4.5, change1M: 0.5 },
      { name: 'Reckitt Benckiser', sector: 'Consumer Staples', value: 208000, weight: 4.0, change1M: -0.2 },
      { name: 'Treasury 4.25% 2034', sector: 'Fixed Income', value: 182000, weight: 3.5, change1M: 0.1 }
    ],
    riskMetrics: {
      volatility: 5.8,
      sharpeRatio: 0.62,
      maxDrawdown: -3.2,
      betaFTSE100: 0.35
    }
  },
  {
    PK: 'CLIENT#CLT004',
    SK: 'PORTFOLIO',
    clientId: 'CLT004',
    allocation: {
      ukEquities: 35,
      internationalEquities: 22,
      fixedIncome: 25,
      alternatives: 12,
      cash: 6
    },
    holdings: [
      { name: 'Vanguard FTSE 100 ETF', sector: 'Index Fund', value: 210000, weight: 12.0, change1M: 1.4 },
      { name: 'Fundsmith Equity', sector: 'Multi-Asset', value: 175000, weight: 10.0, change1M: 1.2 },
      { name: 'iShares Global Corp Bond', sector: 'Fixed Income', value: 157500, weight: 9.0, change1M: 0.3 },
      { name: 'Lloyds Banking Group', sector: 'Financials', value: 140000, weight: 8.0, change1M: -1.8 },
      { name: 'Tesco PLC', sector: 'Consumer Staples', value: 122500, weight: 7.0, change1M: 0.6 },
      { name: 'Aviva PLC', sector: 'Financials', value: 105000, weight: 6.0, change1M: 2.1 },
      { name: 'iShares MSCI World', sector: 'Index Fund', value: 96250, weight: 5.5, change1M: 2.4 },
      { name: 'Persimmon PLC', sector: 'Real Estate', value: 87500, weight: 5.0, change1M: -3.2 },
      { name: 'Jupiter Strategic Bond', sector: 'Fixed Income', value: 78750, weight: 4.5, change1M: 0.4 },
      { name: 'Impax Environmental', sector: 'Alternatives', value: 70000, weight: 4.0, change1M: 1.7 }
    ],
    riskMetrics: {
      volatility: 10.8,
      sharpeRatio: 0.78,
      maxDrawdown: -7.6,
      betaFTSE100: 0.88
    }
  },
  {
    PK: 'CLIENT#CLT005',
    SK: 'PORTFOLIO',
    clientId: 'CLT005',
    allocation: {
      ukEquities: 20,
      internationalEquities: 12,
      fixedIncome: 40,
      alternatives: 18,
      cash: 10
    },
    holdings: [
      { name: 'iShares Index Linked Gilts', sector: 'Fixed Income', value: 1335000, weight: 15.0, change1M: 0.3 },
      { name: 'PIMCO Global Bond', sector: 'Fixed Income', value: 1068000, weight: 12.0, change1M: 0.5 },
      { name: 'Vanguard LifeStrategy 40%', sector: 'Multi-Asset', value: 890000, weight: 10.0, change1M: 0.8 },
      { name: 'Legal & General Property', sector: 'Real Estate', value: 712000, weight: 8.0, change1M: -0.4 },
      { name: 'BHP Group', sector: 'Materials', value: 623000, weight: 7.0, change1M: -1.5 },
      { name: 'GlaxoSmithKline', sector: 'Healthcare', value: 534000, weight: 6.0, change1M: 1.3 },
      { name: 'Bluefield Solar Income', sector: 'Renewables', value: 445000, weight: 5.0, change1M: 0.6 },
      { name: 'HICL Infrastructure', sector: 'Infrastructure', value: 400500, weight: 4.5, change1M: 0.2 },
      { name: 'Royal London Short Duration', sector: 'Fixed Income', value: 356000, weight: 4.0, change1M: 0.1 },
      { name: 'Invesco Physical Gold', sector: 'Commodities', value: 311500, weight: 3.5, change1M: 2.8 }
    ],
    riskMetrics: {
      volatility: 6.4,
      sharpeRatio: 0.71,
      maxDrawdown: -4.1,
      betaFTSE100: 0.42
    }
  }
];

async function seed() {
  const allItems = [...clients, ...portfolios];

  // DynamoDB BatchWriteItem supports max 25 items per request
  const batches = [];
  for (let i = 0; i < allItems.length; i += 25) {
    batches.push(allItems.slice(i, i + 25));
  }

  console.log(`Seeding ${allItems.length} items into table: ${TABLE_NAME}`);

  for (const batch of batches) {
    const params = {
      RequestItems: {
        [TABLE_NAME]: batch.map((item) => ({
          PutRequest: { Item: item }
        }))
      }
    };

    await docClient.send(new BatchWriteCommand(params));
    console.log(`  Written batch of ${batch.length} items`);
  }

  console.log('Seed complete.');
}

seed().catch((err) => {
  console.error('Seed failed:', err);
  process.exit(1);
});
