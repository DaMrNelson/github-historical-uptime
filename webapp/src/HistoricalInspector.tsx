import Tab from "react-bootstrap/Tab";
import Tabs from "react-bootstrap/Tabs";
import { Chart as ChartJS,
  LinearScale,
  TimeScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Colors,
} from "chart.js";
import { Line } from "react-chartjs-2";
import dayjs from "dayjs";
import customParseFormat from "dayjs/plugin/customParseFormat";
import duration from "dayjs/plugin/duration";
import relativeTime from "dayjs/plugin/relativeTime";
import "chartjs-adapter-dayjs-4/dist/chartjs-adapter-dayjs-4.esm";
import annotationPlugin from "chartjs-plugin-annotation";
import { useMemo } from "react";
import { aggregateMonthly, averageMonthly, checkMissingComponents, getDatasets, type Datasets, type HistoricalData } from "./historicalData";

ChartJS.register(
  LinearScale,
  TimeScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Colors,
  annotationPlugin,
);

dayjs.extend(customParseFormat);
dayjs.extend(duration);
dayjs.extend(relativeTime);


const RELEVANT_COMPONENTS = [
    "API Requests",
    "Actions",
    //"Codespaces", // Was not available at the beginning of historical data
    //"Copilot", // Was not available at the beginning of historical data
    "Git Operations",
    "Issues",
    "Packages",
    "Pages",
    "Pull Requests",
    "Webhooks",
];

const MICROSOFT_ACQUISITION_TS = dayjs("October 26, 2018", "MMMM DD YYYY").toDate().getTime();


export const HistoricalInspector = ({ data }: { data: HistoricalData }) => {
  const { datasets, datasetsAvg } = useMemo(() => {
    // Aggregate and validate data
    const monthly = aggregateMonthly(data, RELEVANT_COMPONENTS);
    const numMissing = checkMissingComponents(monthly.monthlyData, RELEVANT_COMPONENTS);

    if (monthly.numConflict + numMissing > 0) {
      if (monthly.numConflict > 0) {
        console.error(`${monthly.numConflict} disagreements about monthly uptimes (indicates a bad scrape)`);
      }

      if (numMissing > 0) {
        console.error(`${numMissing} missing components (indicates a bad scrape)`);
      }

      // TODO: Check gaps between months
      // TODO: Display to user!
    }

    // Build actual datasets for graphs
    const datasets = getDatasets(monthly.monthlyData, RELEVANT_COMPONENTS, false);

    const averageSeriesName = "Average of all Component Uptimes";
    const monthlyAvg = averageMonthly(monthly.monthlyData, averageSeriesName);
    const datasetsAvg = getDatasets(monthlyAvg, [averageSeriesName], true);

    return {
      datasets,
      datasetsAvg,
    };
  }, [data]);

  return (
    <div className="responsiveGraphHack tabWrapper">
      <Tabs defaultActiveKey="average">
        <Tab eventKey="average" title="Average" className="responsiveGraphHack">
          <HistoricalGraph title={["GitHub Average Uptime by Month", "(Codespaces and Copilot excluded due to launch partway through dataset)"]} datasets={datasetsAvg} />
        </Tab>
        <Tab eventKey="breakdown" title="Breakdown" className="responsiveGraphHack">
          <HistoricalGraph title={["GitHub Uptime by Month", "(Codespaces and Copilot excluded due to launch partway through dataset)"]} datasets={datasets} legend />
        </Tab>
      </Tabs>
    </div>
  );
}

export const HistoricalGraph = ({ title, datasets, legend }: { title: string | string[], datasets: Datasets, legend?: boolean }) => {
  const deltaY = datasets.maxY - datasets.minY;
  const yPad = deltaY * 0.1;

  return (
    <Line
      className="responsiveGraphHack"
      style={{ minHeight: 400 }}
      data={{
        datasets: datasets.datasets
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: !!legend,
            position: "top" as const
          },
          title: {
            display: true,
            text: title,
          },
          annotation: {
            annotations: {
              microslopLine: {
                type: "line",
                xMin: MICROSOFT_ACQUISITION_TS,
                xMax: MICROSOFT_ACQUISITION_TS,
                borderColor: "#000000",
                borderDash: [7, 7],
              },
              microslopText: {
                type: "label",
                xValue: MICROSOFT_ACQUISITION_TS,
                yValue: datasets.minY + deltaY / 2,
                xAdjust: 10,
                content: "Microsoft Acquires GitHub",
                rotation: 90,
                font: {
                  size: 14,
                },
                padding: 0,
              },
            }
          },
          tooltip: {
            mode: "index",
            callbacks: {
              title: (tooltipItems) => dayjs((tooltipItems[0].raw as [number, number])[0]).format("MMMM YYYY"),
              label: (tooltipItem) => {
                const raw = tooltipItem.raw as [number, number, number, number];
                const timeMinor = raw[2];
                const timeMajor = raw[3];

                const humanize = (duration: number) => `${dayjs.duration({ seconds: duration }).humanize()}`;
                const labels = [
                  `${tooltipItem.dataset.label}: ${tooltipItem.parsed.y!.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 5 })}`,
                ];

                if (timeMinor > 0) {
                  labels.push(`Partial Outages: ${timeMinor > 0 ? humanize(timeMinor) : "N/A"}`);
                }

                if (timeMajor > 0) {
                  labels.push(`Major Outages: ${timeMajor > 0 ? humanize(timeMajor) : "N/A"}`);
                }

                return labels;
              },
            },
          },
        },
        scales: {
          x: {
            type: "time",
            time: {
              unit: "month"
            }
          },
          y: {
            min: datasets.minY - yPad,
            max: datasets.maxY + yPad,
            ticks: {
              includeBounds: false,
              callback: (tickValue) => (
                tickValue.toLocaleString(undefined, { style: "percent", minimumFractionDigits: 3 })
              ),
            },
          },
        },
      }}
    />
  );
};
