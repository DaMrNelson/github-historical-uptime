import Container from "react-bootstrap/Container";
import Card from "react-bootstrap/Card";
import Spinner from "react-bootstrap/Spinner";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { HistoricalInspector } from "./HistoricalInspector";

const historicalDataClient = new QueryClient()

export const App = () => (
  <QueryClientProvider client={historicalDataClient}>
    <HistoricalDataView />
  </QueryClientProvider>
);

export const HistoricalDataView = () => {
  const { isPending, error, data } = useQuery({
    queryKey: ["chart-main"],
    queryFn: () =>
      fetch(`${import.meta.env.BASE_URL}data/historical-data.json`).then((res) =>
        res.json()
      )
  });

  return (
    <>
      <Container className="responsiveGraphHack" style={{ minHeight: "100%", padding: "1rem 0", justifyContent: "flex-start" }}>
        <div style={{ flex: "1 0 auto", textAlign: "center", overflow: "hidden" }}>
          <h1 className="display-4">GitHub's Historic Uptime</h1>
          <p>
            All data sourced from the <a target="_blank" href="https://www.githubstatus.com/uptime">official status page</a>.
          </p>
        </div>

        <Card className="responsiveGraphHack" style={{ margin: "1rem", flex: "1 0" }}>
          <Card.Body className="responsiveGraphHack">
            { isPending ?
              <div style={{ display: "flex", flexDirection: "row", justifyContent: "center" }}>
                <Spinner animation="border" variant="primary" role="status">
                  <span className="visually-hidden">Loading...</span>
                </Spinner>
              </div>
            : error ?
              <>
                <h3>Failed to Load Historical Data</h3>
                <p>Error:</p>
                <pre>{JSON.stringify(error)}</pre>
              </>
            :
              <HistoricalInspector data={data} />
            }
          </Card.Body>
        </Card>
      </Container>

      <p style={{ textAlign: "center", paddingBottom: "1rem" }}>
        <i><a href="https://github.com/DaMrNelson/github-historical-uptime" style={{ color: "var(--bs-secondary)" }}>View source</a></i>
      </p>
    </>
  );
};

export default App;
