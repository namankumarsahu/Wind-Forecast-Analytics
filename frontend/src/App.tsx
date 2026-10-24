import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { EmptyState } from "./components/ui";
import Accuracy from "./pages/Accuracy";
import Explorer from "./pages/Explorer";
import Overview from "./pages/Overview";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="explorer" element={<Explorer />} />
        <Route path="accuracy" element={<Accuracy />} />
        <Route path="*" element={<EmptyState title="Page not found">Use the navigation above to return to the dashboard.</EmptyState>} />
      </Route>
    </Routes>
  );
}
