"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import { toast } from "sonner";
import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  ColumnDef,
  getPaginationRowModel,
} from "@tanstack/react-table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import {
  Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Check,
  X,
  Plus,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface TrainingJob {
  id: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  status: string;
  logs: string;
  params: Record<string, any>;
  app: string;
  model_version: string | null;
  initiated_by: number;
}

export default function TrainingJobsPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const [jobs, setJobs] = useState<TrainingJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [trainDialogOpen, setTrainDialogOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState<TrainingJob | null>(null);
  const [refreshFlag, setRefreshFlag] = useState(false);
  const [trainingLoading, setTrainingLoading] = useState(false);
  const [appSlugs, setAppSlugs] = useState<{ slug: string; id: string }[]>([]);

  const [trainParams, setTrainParams] = useState({
    app_slug: "",
    epochs: 10,
    batch_size: 32,
    learning_rate: 0.001,
    test_split: 0.2,
    model_type: "bert-base-uncased",
  });

  // Fetch jobs
  useEffect(() => {
    async function fetchJobs() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE_URL}/guardrails/training/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch training jobs");
        const data = await res.json();
        setJobs(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();
  }, [refreshFlag, API_BASE_URL, token]);

  // Fetch available slugs for dropdown
  useEffect(() => {
    async function fetchSlugs() {
      try {
        const res = await fetch(`${API_BASE_URL}/guardrails/apps/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch app slugs");
        const data = await res.json();
        setAppSlugs(data);
      } catch (err: any) {
        console.error("Error fetching slugs:", err);
      }
    }
    fetchSlugs();
  }, [token]);

  // Fetch job details
  const fetchJobDetails = useCallback(
    async (id: string) => {
      try {
        const res = await fetch(`${API_BASE_URL}/guardrails/training/${id}/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch job details");
        const data = await res.json();
        setSelectedJob(data);
      } catch (err: any) {
        toast.error(err.message || "Failed to fetch details");
      }
    },
    [API_BASE_URL, token]
  );

  // Start training
  const startTraining = async () => {
    try {
      setTrainingLoading(true);
      const res = await fetch(`${API_BASE_URL}/guardrails/apps/${trainParams.app_slug}/train/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          ...trainParams,
          epochs: Number(trainParams.epochs),
          batch_size: Number(trainParams.batch_size),
          learning_rate: Number(trainParams.learning_rate),
          test_split: Number(trainParams.test_split),
        }),
      });

      if (!res.ok) throw new Error("Failed to start training");
      const data = await res.json();
      toast.success(`Training job ${data.id} started successfully`);
      setTrainDialogOpen(false);
      setDialogOpen(false);
      setRefreshFlag((p) => !p);
    } catch (err: any) {
      toast.error(err.message || "Error starting training job");
    } finally {
      setTrainingLoading(false);
    }
  };

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setTrainParams({ ...trainParams, [e.target.name]: e.target.value });
  };

  // Columns
  const columns = useMemo<ColumnDef<TrainingJob>[]>(
    () => [
      {
        id: "serial",
        header: "Sr. No.",
        accessorFn: (_row, index) => index + 1,
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground">{getValue<number>()}</div>
        ),
        size: 70,
      },
      {
        header: "Job ID",
        accessorKey: "id",
        cell: ({ getValue }) => (
          <div className="text-center font-mono text-xs text-muted-foreground">
            {getValue() || "-"}
          </div>
        ),
      },
      {
        header: "Created At",
        accessorKey: "created_at",
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground">
            {new Date(getValue() as string).toLocaleString("en-IN", {
              day: "2-digit",
              month: "short",
              year: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </div>
        ),
      },
      {
        header: "Status",
        accessorKey: "status",
        cell: ({ getValue }) => {
          const status = getValue() as string;
          const color =
            status === "done"
              ? "text-green-600"
              : status === "failed"
              ? "text-red-600"
              : "text-yellow-600";
          return (
            <div className={`text-center font-semibold ${color} capitalize`}>
              {status}
            </div>
          );
        },
      },
      {
        header: "Model Type",
        accessorFn: (row) => row.params?.model_type || "-",
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground text-sm">
            {getValue() || "-"}
          </div>
        ),
      },
      {
        header: "Model Version",
        accessorKey: "model_version",
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground">{getValue() || "-"}</div>
        ),
      },
    ],
    []
  );

  const table = useReactTable({
    data: jobs,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Training Jobs</h1>
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            View and manage all model training jobs.
          </p>
          <Button
            onClick={() => setTrainDialogOpen(true)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2"
          >
            <Plus className="h-4 w-4" /> Start New Training
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border border-border/50 bg-background shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex justify-center items-center h-48 text-muted-foreground">
            <Loader2 className="animate-spin mr-2" /> Loading training jobs...
          </div>
        ) : error ? (
          <div className="text-center text-red-500 py-6">{error}</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <Table className="w-full table-auto">
                <TableHeader className="bg-muted/50">
                  {table.getHeaderGroups().map((hg) => (
                    <TableRow key={hg.id}>
                      {hg.headers.map((header) => (
                        <TableHead key={header.id} className="font-semibold text-center">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </TableHead>
                      ))}
                    </TableRow>
                  ))}
                </TableHeader>

                <TableBody>
                  {table.getRowModel().rows.length ? (
                    table.getRowModel().rows.map((row) => (
                      <TableRow
                        key={row.id}
                        onClick={async () => {
                          await fetchJobDetails(row.original.id);
                          setDialogOpen(true);
                        }}
                        className="cursor-pointer even:bg-muted/30 hover:bg-muted/50 transition-colors"
                      >
                        {row.getVisibleCells().map((cell) => (
                          <TableCell key={cell.id} className="text-center">
                            {flexRender(cell.column.columnDef.cell, cell.getContext())}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={columns.length}
                        className="h-24 text-center text-muted-foreground"
                      >
                        No training jobs found.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between px-4 py-3 border-t bg-muted/10">
              <div className="text-sm text-muted-foreground">
                Showing{" "}
                {table.getState().pagination.pageIndex *
                  table.getState().pagination.pageSize +
                  1}{" "}
                to{" "}
                {Math.min(
                  (table.getState().pagination.pageIndex + 1) *
                    table.getState().pagination.pageSize,
                  table.getFilteredRowModel().rows.length
                )}{" "}
                of {table.getFilteredRowModel().rows.length} entries
              </div>
              <div className="flex items-center space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.setPageIndex(0)}
                  disabled={!table.getCanPreviousPage()}
                >
                  <ChevronsLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <div className="text-sm font-medium">
                  Page {table.getState().pagination.pageIndex + 1} of{" "}
                  {table.getPageCount()}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                  disabled={!table.getCanNextPage()}
                >
                  <ChevronsRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Job Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl p-6 max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Training Job Details</DialogTitle>
            <DialogDescription>
              View details and parameters of this training job.
            </DialogDescription>
          </DialogHeader>

          {selectedJob ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
              {/* Left: Job Info */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-blue-600 mb-2">
                  Job Information
                </h3>
                {Object.entries(selectedJob)
                  .filter(([k]) => k !== "params" && k !== "logs")
                  .map(([key, value]) => (
                    <div
                      key={key}
                      className="border-b border-border/40 pb-2 last:border-0 flex flex-col"
                    >
                      <span className="text-sm font-semibold text-muted-foreground capitalize">
                        {key.replace(/_/g, " ")}
                      </span>
                      <span className="text-sm text-foreground break-all">
                        {typeof value === "object"
                          ? JSON.stringify(value, null, 2)
                          : String(value || "-")}
                      </span>
                    </div>
                  ))}
              </div>

              {/* Right: Params */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-indigo-600 mb-2">
                  Training Parameters
                </h3>
                {selectedJob.params && Object.keys(selectedJob.params).length > 0 ? (
                  Object.entries(selectedJob.params).map(([k, v]) => (
                    <div
                      key={k}
                      className="border-b border-border/40 pb-2 last:border-0 flex justify-between text-sm"
                    >
                      <span className="font-medium text-muted-foreground capitalize">
                        {k.replace(/_/g, " ")}
                      </span>
                      <span className="text-foreground font-mono text-xs">
                        {String(v)}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No parameters available</p>
                )}
              </div>

              {/* Logs */}
              {selectedJob.logs && (
                <div className="col-span-full space-y-2">
                  <h3 className="text-sm font-semibold text-green-600">Logs</h3>
                  <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto max-h-48">
                    {selectedJob.logs}
                  </pre>
                </div>
              )}
            </div>
          ) : (
            <div className="flex justify-center items-center text-muted-foreground py-6">
              <Loader2 className="animate-spin mr-2" /> Loading details...
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Training Form Dialog */}
      <Dialog open={trainDialogOpen} onOpenChange={setTrainDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start New Training</DialogTitle>
            <DialogDescription>
              Select app and adjust parameters to start a new training job.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 mt-4">
            <div className="space-y-1">
              <Label htmlFor="app_slug">App Slug</Label>
              <select
                id="app_slug"
                name="app_slug"
                value={trainParams.app_slug}
                onChange={handleParamChange}
                className="w-full border rounded-md p-2 bg-background text-foreground"
              >
                <option value="">Select App</option>
                {appSlugs.map((app) => (
                  <option key={app.id} value={app.slug}>
                    {app.slug}
                  </option>
                ))}
              </select>
            </div>

            {Object.entries(trainParams)
              .filter(([key]) => key !== "app_slug")
              .map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <Label htmlFor={key} className="capitalize text-sm font-medium">
                    {key.replace(/_/g, " ")}
                  </Label>
                  <Input
                    id={key}
                    name={key}
                    type={key === "model_type" ? "text" : "number"}
                    step={["learning_rate", "test_split"].includes(key) ? "0.001" : "1"}
                    value={value}
                    onChange={handleParamChange}
                    className="w-full"
                  />
                </div>
              ))}

            <div className="flex justify-end gap-2 pt-4">
              <Button
                className="bg-red-600 hover:bg-red-700 text-white"
                onClick={() => setTrainDialogOpen(false)}
              >
                <X className="w-4 h-4 mr-1" /> Cancel
              </Button>
              <Button
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={startTraining}
                disabled={trainingLoading}
              >
                {trainingLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Check className="w-4 h-4 mr-1" /> Save
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}