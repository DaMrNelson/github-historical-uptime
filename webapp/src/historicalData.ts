import type { ChartData } from "chart.js";
import dayjs from "dayjs";

export type HistoricalData = HistoricalPage[];

export type HistoricalPage = {
  component: {
    name: string
  },
  months: HistoricalMonth[],
};

export type HistoricalMonth = {
  name: string,
  year: number,
  uptime_percentage: number,
  days: HistoricalDay[]
};

export type HistoricalDay = {
  color: string,
  date?: string,
  events?: unknown[],
  p?: number,
  m?: number,
}

export type MonthlyData = Record<string, MonthlyEntry>;

export type MonthlyEntry = {
  month: string,
  year: number,
  componentUptimes: Record<string, number>,
  componentMinorSeconds: Record<string, number>,
  componentMajorSeconds: Record<string, number>,
};

export type Dataset = (ChartData<"line", { key: number, value: number }>)["datasets"][number];
export type Datasets = {
  datasets: Dataset[],
  minX: number,
  minY: number,
  maxX: number,
  maxY: number,
};

// Colors from bootstrap
const COLOR_OK = "#198754";
const COLOR_MINOR = "#ffc107";
const COLOR_MAJOR = "#dc3545";

export const aggregateMonthly = (data: HistoricalData, selectedCompNames: string[]): { monthlyData: MonthlyData, numConflict: number } => {
  const monthlyData: MonthlyData = {};
  let numConflict = 0;

  for (const page of data) {
    // Filter for relevant components
    const compName = page["component"]["name"];

    if (!selectedCompNames.includes(compName)) {
      continue;
    }

    // Add to relevant bin, creating it if needed
    for (const month of page["months"]) {
      const groupName = `${month.year}:${month.name}`;

      // Filter out incomplete months
      let incompleteMonth = false;

      for (const day of month["days"]) {
        if (day.events === undefined) {
          incompleteMonth = true;
          break;
        }
      }

      if (incompleteMonth) {
        console.warn(`Skip month ${groupName} with incomplete data`);
        continue;
      }

      // Find monthly bin first
      let group = monthlyData[groupName];

      if (group === undefined) {
        group = {
          month: month.name,
          year: month.year,
          componentUptimes: {},
          componentMinorSeconds: {},
          componentMajorSeconds: {},
        }
        monthlyData[groupName] = group;
      }

      // Update component uptime entry for the bin
      const uptime = month.uptime_percentage;
      const existingUptime = group.componentUptimes[compName];

      if (existingUptime !== undefined && existingUptime !== uptime) {
        console.warn(`Conflicting uptime! Month ${groupName} already registered as ${existingUptime}, but was also declared as ${uptime}`);
        numConflict++;
      }

      group.componentUptimes[compName] = uptime;

      // Aggregate minor and major outages
      let minorSeconds = 0;
      let majorSeconds = 0;

      for (const day of month.days) {
        minorSeconds += day.p ?? 0;
        majorSeconds += day.m ?? 0;
      }

      group.componentMinorSeconds[compName] = minorSeconds;
      group.componentMajorSeconds[compName] = majorSeconds;
    }
  };

  return { monthlyData, numConflict };
};

export const checkMissingComponents = (monthlyData: MonthlyData, selectedCompNames: string[]): number => {
  let numMissing = 0;

  for (const groupName in monthlyData) {
    const group = monthlyData[groupName];

    for (const compName of selectedCompNames) {
      if (group.componentUptimes[compName] === undefined) {
        console.warn(`WARNING: Missing data for ${compName} at ${groupName}`);
        numMissing++;
      }
    }
  }

  return numMissing;
};

export const averageMonthly = (monthlyData: MonthlyData, avgCompName: string): MonthlyData => {
  const avgMonthlyData: MonthlyData = {};

  for (const groupName in monthlyData) {
    const group = monthlyData[groupName];
    const compNames = Object.keys(monthlyData[groupName].componentUptimes);
    const avg = compNames.reduce((sum, compName) => sum + group.componentUptimes[compName], 0) / compNames.length;
    const totalMinorSeconds = compNames.reduce((sum, compName) => sum + group.componentMinorSeconds[compName], 0);
    const totalMajorSeconds = compNames.reduce((sum, compName) => sum + group.componentMajorSeconds[compName], 0)
    avgMonthlyData[groupName] = {
      ...group,
      componentUptimes: {
        [avgCompName]: avg,
      },
      componentMinorSeconds: {
        [avgCompName]: totalMinorSeconds,
      },
      componentMajorSeconds: {
        [avgCompName]: totalMajorSeconds,
      },
    };
  }

  return avgMonthlyData;
};

export const getDatasets = (monthlyData: MonthlyData, selectedCompNames: string[], color: boolean): Datasets => {
  const datasets: Dataset[] = [];
  let minX = Number.MAX_SAFE_INTEGER;
  let minY = 1;
  let maxX = 0;
  let maxY = 0;

  for (const compName of selectedCompNames) {
    type DpData = {
      x: number,
      y: number,
      color: string,
      minorSeconds: number,
      majorSeconds: number,
    };
    const dpData: DpData[] = [];

    for (const groupName in monthlyData) {
      // Get datapoint
      const date = dayjs(groupName, "YYYY:MMMM");
      const ts = date.toDate().getTime();
      const group = monthlyData[groupName];
      const uptime = group.componentUptimes[compName];

      // Determine color
      let color = COLOR_OK;
      const minorSeconds = group.componentMinorSeconds[compName];
      const majorSeconds = group.componentMajorSeconds[compName];

      if (majorSeconds > 0) {
        color = COLOR_MAJOR;
      } else if (minorSeconds > 0) {
        color = COLOR_MINOR;
      }

      dpData.push({
        x: ts,
        y: uptime,
        color,
        minorSeconds, majorSeconds,
      });

      // Adjust min and max bounds
      if (ts < minX)
        minX = ts;
      if (uptime < minY)
        minY = uptime;
      if (ts > maxX)
        maxX = ts;
      if (uptime > maxY)
        maxY = uptime;
    }

    dpData.sort((a, b) => a.x - b.x); // Ascending
    const dataset: Dataset = {
      label: compName,
      data: dpData.map((dp) => [dp.x, dp.y, dp.minorSeconds, dp.majorSeconds]) as unknown as Dataset["data"],
    };

    if (color) {
      Object.assign(dataset, {
        pointBackgroundColor: dpData.map((dp) => dp.color),
        pointBorderColor: dpData.map((dp) => dp.color),
        segment: {
          borderColor: ctx => dpData[ctx.p1DataIndex].color,
        },
      } as Partial<Dataset>);
    }
    datasets.push(dataset);
  };

  return { datasets, minX, minY, maxX, maxY };
};
