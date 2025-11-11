"use client";

import React, { useEffect, useState, useMemo } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Filter,
  Loader2,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Check, 
  X,
} from "lucide-react";
import { toast } from "sonner";

export default function LLMResponsesPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const [responses, setResponses] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);
  const [filters, setFilters] = useState({ app: "", labeled: "" });
  const [selectedResponse, setSelectedResponse] = useState<any | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showActionDialog, setShowActionDialog] = useState<"label" | "evaluate" | null>(null);
  const [labelData, setLabelData] = useState({ label: "", action: "" });


  // Fetch responses
  const fetchResponses = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filters.app) params.append("app", filters.app);
      if (filters.labeled) params.append("labeled", filters.labeled);

      const res = await fetch(
        `${API_BASE_URL}/guardrails/responses/?${params.toString()}`,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      if (!res.ok) throw new Error("Failed to fetch responses");
      const data = await res.json();
      setResponses(data);
    } catch (err) {
      console.error(err);
      toast.error("Error fetching responses");
    } finally {
      setLoading(false);
    }
  };

  // Fetch response details
  const fetchResponseDetails = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/guardrails/responses/${id}/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch details");
      const data = await res.json();
      setSelectedResponse(data);
      setDialogOpen(true);
    } catch (err) {
      console.error(err);
      toast.error("Error loading response details");
    }
  };

  // Label
  const handleLabel = async () => {
    if (!selectedResponse) return;
    try {
      const res = await fetch(
        `${API_BASE_URL}/guardrails/responses/${selectedResponse.id}/label/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ label: "testing", action: "info" }),
        }
      );
      if (!res.ok) throw new Error("Failed to label");
      toast.success("Label applied successfully");
      setDialogOpen(false);
      fetchResponses();
    } catch (err) {
      console.error(err);
      toast.error("Error labeling response");
    }
  };

  // Evaluate
  const handleEvaluate = async () => {
    if (!selectedResponse) return;
    try {
      const res = await fetch(
        `${API_BASE_URL}/guardrails/responses/${selectedResponse.id}/evaluate/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ label: "testing", action: "info" }),
        }
      );
      if (!res.ok) throw new Error("Failed to evaluate");
      toast.success("Evaluation triggered successfully");
      setDialogOpen(false);
      fetchResponses();
    } catch (err) {
      console.error(err);
      toast.error("Error evaluating response");
    }
  };

  useEffect(() => {
    fetchResponses();
  }, [filters]);

  useEffect(() => {
    if (showActionDialog) {
      setLabelData({ label: "", action: "" });
    }
  }, [showActionDialog]);

  // Columns
  const columns = useMemo<ColumnDef<any>[]>(
    () => [
      {
        header: "Sr. No.",
        accessorFn: (_row, index) => index + 1,
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground">{getValue<number>()}</div>
        ),
        size: 80,
      },
      { accessorKey: "request_id", header: "Request ID" },
      {
      accessorKey: "prompt",
      header: "Prompt",
      cell: ({ getValue }) => (
        <span className="text-muted-foreground font-mono text-sm">
            {getValue() || "-"}
        </span>
      ),
    },
    {
    accessorKey: "response_text",
    header: "Response",
    cell: ({ getValue }) => (
        <span className="text-muted-foreground font-mono text-sm truncate max-w-sm block">
        {getValue() || "-"}
        </span>
    ),
    },
      {
        accessorKey: "predicted_label",
        header: () => <div className="text-center">Predicted Label</div>,
        cell: ({ getValue }) => (
          <div className="text-center font-medium">{getValue() || "-"}</div>
        ),
      },
      {
        accessorKey: "evaluated",
        header: () => <div className="text-center">Evaluated</div>,
        cell: ({ getValue }) =>
          getValue() ? (
            <div className="flex justify-center">
              <CheckCircle className="text-green-600 w-4 h-4" />
            </div>
          ) : (
            <div className="flex justify-center">
              <XCircle className="text-red-500 w-4 h-4" />
            </div>
          ),
      },
      {
        accessorKey: "labeled",
        header: () => <div className="text-center">Labeled</div>,
        cell: ({ getValue }) =>
          getValue() ? (
            <div className="flex justify-center">
              <CheckCircle className="text-green-600 w-4 h-4" />
            </div>
          ) : (
            <div className="flex justify-center">
              <XCircle className="text-red-500 w-4 h-4" />
            </div>
          ),
      },
    ],
    []
  );

  // Table setup
  const table = useReactTable({
    data: responses,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight mb-1">LLM Responses</h1>
        <div className="flex items-center justify-between">
          <p className="text-muted-foreground">
            Review and manage model responses captured via Kobra Guardrails.
          </p>
          {!filterOpen && (
            <Button
              onClick={() => setFilterOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2"
            >
              <Filter className="h-4 w-4" /> Filters
            </Button>
          )}
        </div>
      </div>

      {/* Filters */}
      {filterOpen && (
        <div className="border rounded-lg bg-muted/20 shadow-sm animate-in fade-in-50">
          <div className="p-4 pb-2 border-b flex items-center justify-between bg-muted/30 rounded-t-lg">
            <h2 className="text-base font-semibold tracking-tight text-foreground flex items-center gap-2">
              <Filter className="h-4 w-4 text-indigo-600" />
              Filters
            </h2>
            <Button
              size="sm"
              onClick={() => setFilterOpen(false)}
              className="bg-gray-200 hover:bg-gray-300 text-gray-900 font-medium"
            >
              Close
            </Button>
          </div>
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="app" className="text-sm font-medium text-foreground">
                  App Slug
                </Label>
                <Input
                  id="app"
                  value={filters.app}
                  onChange={(e) => setFilters({ ...filters, app: e.target.value })}
                  placeholder="e.g., chatbot"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="labeled" className="text-sm font-medium text-foreground">
                  Labeled
                </Label>
                <Input
                  id="labeled"
                  value={filters.labeled}
                  onChange={(e) =>
                    setFilters({ ...filters, labeled: e.target.value })
                  }
                  placeholder="true / false"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="rounded-md border border-border/50 bg-background shadow-sm">
        <Table>
          <TableHeader className="bg-muted/50">
            {table.getHeaderGroups().map((hg) => (
              <TableRow key={hg.id}>
                {hg.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={`font-semibold ${
                        header.column.id === "predicted_label" ||
                        header.column.id === "evaluated" ||
                        header.column.id === "labeled" ||
                        header.column.id === "srno" ||
                        header.index === 0            
                        ? "text-center"
                        : "text-left"
                    }`}
                   >

                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>

          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={columns.length} className="text-center py-6">
                  <Loader2 className="animate-spin inline-block mr-2" />
                  Loading responses...
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={() => fetchResponseDetails(row.original.id)}
                  className="cursor-pointer even:bg-muted/30 hover:bg-muted/40 transition-colors"
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="text-center text-muted-foreground h-24"
                >
                  No responses found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        <div className="flex items-center justify-between px-2 py-3 border-t bg-muted/10 rounded-b-md">
          <div className="text-sm text-muted-foreground">
            Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{" "}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
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

            <div className="flex items-center gap-1 text-sm">
              <span className="text-muted-foreground">Page</span>
              <span className="font-medium">
                {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
              </span>
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
      </div>

      {/* Details Dialog */}
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-4xl p-6">
            <DialogHeader>
            <DialogTitle>Response Details</DialogTitle>
            </DialogHeader>

            {selectedResponse ? (
            <div className="grid grid-cols-2 gap-6 mt-4">
                {/* Left column */}
                <div className="space-y-3">
                {Object.entries(selectedResponse)
                    .slice(0, Math.ceil(Object.entries(selectedResponse).length / 2))
                    .map(([key, value]) => {
                    const displayValue =
                        value === null || value === undefined
                        ? "-"
                        : typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : String(value);
                    return (
                        <div
                        key={key}
                        className="border-b border-border/40 pb-2 last:border-0 flex flex-col"
                        >
                        <span className="text-sm font-semibold text-muted-foreground capitalize">
                            {key.replace(/_/g, " ")}
                        </span>
                        <span className="text-sm text-foreground break-all">
                            {displayValue}
                        </span>
                        </div>
                    );
                    })}
                </div>

                {/* Right column */}
                <div className="space-y-3">
                {Object.entries(selectedResponse)
                    .slice(Math.ceil(Object.entries(selectedResponse).length / 2))
                    .map(([key, value]) => {
                    const displayValue =
                        value === null || value === undefined
                        ? "-"
                        : typeof value === "object"
                        ? JSON.stringify(value, null, 2)
                        : String(value);
                    return (
                        <div
                        key={key}
                        className="border-b border-border/40 pb-2 last:border-0 flex flex-col"
                        >
                        <span className="text-sm font-semibold text-muted-foreground capitalize">
                            {key.replace(/_/g, " ")}
                        </span>
                        <span className="text-sm text-foreground break-all">
                            {displayValue}
                        </span>
                        </div>
                    );
                    })}
                </div>
            </div>
            ) : (
            <div className="text-center py-6 text-muted-foreground">
                Loading details...
            </div>
            )}

            <div className="flex justify-end gap-3 pt-6">
            <Button
                onClick={() => {
                setShowActionDialog("label");
                }}
                className="bg-blue-600 hover:bg-blue-700 text-white px-5"
            >
                Label
            </Button>
            <Button
                onClick={() => {
                setShowActionDialog("evaluate");
                }}
                className="bg-purple-600 hover:bg-purple-700 text-white px-5"
            >
                Evaluate
            </Button>
            </div>
        </DialogContent>
        </Dialog>

        {/* Label/Evaluate Input Dialog */}
        <Dialog open={!!showActionDialog} onOpenChange={() => setShowActionDialog(null)}>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>
                {showActionDialog === "label" ? "Apply Label" : "Trigger Evaluation"}
              </DialogTitle>
            </DialogHeader>

            <div className="space-y-4 mt-2">
              <div className="space-y-2">
                <Label htmlFor="label">Label</Label>
                <Input
                  id="label"
                  placeholder="Enter label"
                  value={labelData.label}
                  onChange={(e) => setLabelData({ ...labelData, label: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="action">Action</Label>
                <select
                  id="action"
                  value={labelData.action}
                  onChange={(e) => setLabelData({ ...labelData, action: e.target.value })}
                  className="w-full border rounded-md p-2 bg-background text-foreground"
                >
                  <option value="">Select Action</option>
                  <option value="info">Info</option>
                  <option value="warning">Warning</option>
                  <option value="block">Block</option>
                </select>
              </div>
            </div>

            {/* Action buttons */}
            <div className="flex justify-end gap-3 pt-4">
              <Button
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={async () => {
                  try {
                    const endpoint =
                      showActionDialog === "label"
                        ? `${API_BASE_URL}/guardrails/responses/${selectedResponse.id}/label/`
                        : `${API_BASE_URL}/guardrails/responses/${selectedResponse.id}/evaluate/`;

                    const res = await fetch(endpoint, {
                      method: "POST",
                      headers: {
                        "Content-Type": "application/json",
                        Authorization: `Bearer ${token}`,
                      },
                      body: JSON.stringify(labelData),
                    });

                    if (!res.ok) throw new Error("Request failed");

                    toast.success(
                      showActionDialog === "label"
                        ? "Label applied successfully"
                        : "Evaluation triggered successfully"
                    );

                    setLabelData({ label: "", action: "" });
                    setShowActionDialog(null);
                    setDialogOpen(false);
                    fetchResponses();
                  } catch (err) {
                    console.error(err);
                    toast.error("Action failed. Try again.");
                  }
                }}
                disabled={!labelData.label || !labelData.action}
              >
                <Check className="w-4 h-4 mr-1" /> Save
              </Button>

              <Button
                className="bg-red-600 hover:bg-red-700 text-white"
                onClick={() => {
                  setLabelData({ label: "", action: "" });
                  setShowActionDialog(null);
                }}
              >
                <X className="w-4 h-4 mr-1" /> Cancel
              </Button>
            </div>
          </DialogContent>
        </Dialog>
    </div>
  );
}