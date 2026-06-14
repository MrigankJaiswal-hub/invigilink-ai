import TokenInput from "../components/TokenInput";
import CsvUploader from "../components/CSVUploader";

export default function UploadPage() {
  return (
    <div className="space-y-6">
      <TokenInput />
      <CsvUploader />
    </div>
  );
}

