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
  ArrowRightLeft,
} from "lucide-react";
import { Label } from "@/components/ui/label";

interface Model {
  id: string;
  version: string;
  app_name: string;
  app_slug: string;
  categories: string[];
  metrics: Record<string, any>;
  model_files: string[];
  created_at: string;
}

interface Assignment {
  id: number;
  source_model_version: string;
  source_app_slug: string;
  target_app_slug: string;
  assigned_by_username: string;
  assigned_at: string;
}

export default function AvailableModelsPage() {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL;
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const [models, setModels] = useState<Model[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [selectedModelCategories, setSelectedModelCategories] = useState<any>(null);
  const [refreshFlag, setRefreshFlag] = useState(false);
  const [assignLoading, setAssignLoading] = useState(false);
  const [appSlugs, setAppSlugs] = useState<{ slug: string; id: string }[]>([]);
  const [selectedTargetSlug, setSelectedTargetSlug] = useState("");
  const [modelToAssign, setModelToAssign] = useState<Model | null>(null);

  // Fetch models
  useEffect(() => {
    async function fetchModels() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE_URL}/model-orch/models/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch models");
        const data = await res.json();
        setModels(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchModels();
  }, [refreshFlag, API_BASE_URL, token]);

  // Fetch assignments
  useEffect(() => {
    async function fetchAssignments() {
      try {
        const res = await fetch(`${API_BASE_URL}/model-orch/assignments/`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch assignments");
        const data = await res.json();
        setAssignments(data);
      } catch (err: any) {
        console.error("Error fetching assignments:", err);
      }
    }
    fetchAssignments();
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
  }, [API_BASE_URL, token]);

  // Fetch model details and categories
  const fetchModelDetails = useCallback(
    async (model: Model) => {
      try {
        setSelectedModel(model);
        
        // Fetch categories
        const res = await fetch(
          `${API_BASE_URL}/model-orch/models/${model.id}/categories/`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );
        if (!res.ok) throw new Error("Failed to fetch model categories");
        const data = await res.json();
        setSelectedModelCategories(data);
      } catch (err: any) {
        toast.error(err.message || "Failed to fetch details");
      }
    },
    [API_BASE_URL, token]
  );

  // Assign model to app
  const assignModel = async () => {
    if (!modelToAssign || !selectedTargetSlug) {
      toast.error("Please select a target app");
      return;
    }

    try {
      setAssignLoading(true);
      const res = await fetch(
        `${API_BASE_URL}/model-orch/models/${modelToAssign.id}/assign/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            target_app_slug: selectedTargetSlug,
          }),
        }
      );

      if (!res.ok) throw new Error("Failed to assign model");
      const data = await res.json();
      toast.success(data.detail || "Model assigned successfully");
      setAssignDialogOpen(false);
      setSelectedTargetSlug("");
      setRefreshFlag((p) => !p);
    } catch (err: any) {
      toast.error(err.message || "Error assigning model");
    } finally {
      setAssignLoading(false);
    }
  };

  // Get assignments for a model
  const getModelAssignments = (modelVersion: string) => {
    return assignments.filter((a) => a.source_model_version === modelVersion);
  };

  // Columns
  const columns = useMemo<ColumnDef<Model>[]>(
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
        header: "Model ID",
        accessorKey: "id",
        cell: ({ getValue }) => (
            <div className="text-center font-mono text-xs text-muted-foreground break-all">
            {getValue() as string}
            </div>
        ),
      },
      {
        header: "Version",
        accessorKey: "version",
        cell: ({ getValue }) => (
          <div className="text-center font-semibold text-sm">
            {getValue() || "-"}
          </div>
        ),
      },
      {
        header: "App Name",
        accessorKey: "app_name",
        cell: ({ getValue }) => (
          <div className="text-center text-muted-foreground">
            {getValue() || "-"}
          </div>
        ),
      },
      {
        header: "App Slug",
        accessorKey: "app_slug",
        cell: ({ getValue }) => (
          <div className="text-center text-sm font-mono text-muted-foreground">
            {getValue() || "-"}
          </div>
        ),
      },
      {
        header: "Categories",
        accessorKey: "categories",
        cell: ({ getValue }) => {
          const categories = getValue() as string[];
          return (
            <div className="text-center text-sm text-muted-foreground">
              {categories.length > 0 ? categories.length : "-"}
            </div>
          );
        },
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
        id: "actions",
        header: "Actions",
        cell: ({ row }) => (
            <div className="flex justify-center">
            <Button
                size="sm"
                className="bg-blue-600 hover:bg-blue-700 text-white flex items-center gap-1"
                onClick={(e) => {
                e.stopPropagation();
                setModelToAssign(row.original);
                setAssignDialogOpen(true);
                }}
            >
                <ArrowRightLeft className="h-4 w-4" /> Assign
            </Button>
            </div>
        ),
      },
    ],
    []
  );

  const table = useReactTable({
    data: models,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 10 } },
  });

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Available Models</h1>
        <p className="text-muted-foreground">
          View and manage all trained models and their assignments.
        </p>
      </div>

      {/* Table */}
      <div className="rounded-md border border-border/50 bg-background shadow-sm overflow-hidden">
        {loading ? (
          <div className="flex justify-center items-center h-48 text-muted-foreground">
            <Loader2 className="animate-spin mr-2" /> Loading models...
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
                          await fetchModelDetails(row.original);
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
                        No models found.
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

      {/* Model Details Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-5xl p-6 max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Model Details</DialogTitle>
            <DialogDescription>
              View detailed information about this model.
            </DialogDescription>
          </DialogHeader>

          {selectedModel ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
              {/* Left: Model Info */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-blue-600 mb-2">
                  Model Information
                </h3>
                <div className="border-b border-border/40 pb-2 flex flex-col">
                  <span className="text-sm font-semibold text-muted-foreground">ID</span>
                  <span className="text-sm text-foreground break-all font-mono">
                    {selectedModel.id}
                  </span>
                </div>
                <div className="border-b border-border/40 pb-2 flex flex-col">
                  <span className="text-sm font-semibold text-muted-foreground">Version</span>
                  <span className="text-sm text-foreground">
                    {selectedModel.version}
                  </span>
                </div>
                <div className="border-b border-border/40 pb-2 flex flex-col">
                  <span className="text-sm font-semibold text-muted-foreground">App Name</span>
                  <span className="text-sm text-foreground">
                    {selectedModel.app_name || "-"}
                  </span>
                </div>
                <div className="border-b border-border/40 pb-2 flex flex-col">
                  <span className="text-sm font-semibold text-muted-foreground">App Slug</span>
                  <span className="text-sm text-foreground font-mono">
                    {selectedModel.app_slug}
                  </span>
                </div>
                <div className="border-b border-border/40 pb-2 flex flex-col">
                  <span className="text-sm font-semibold text-muted-foreground">Created At</span>
                  <span className="text-sm text-foreground">
                    {new Date(selectedModel.created_at).toLocaleString("en-IN")}
                  </span>
                </div>
              </div>

              {/* Right: Metrics & Categories */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-indigo-600 mb-2">
                  Metrics
                </h3>
                {selectedModel.metrics && Object.keys(selectedModel.metrics).length > 0 ? (
                  Object.entries(selectedModel.metrics).map(([k, v]) => (
                    <div
                      key={k}
                      className="border-b border-border/40 pb-2 last:border-0 flex justify-between text-sm"
                    >
                      <span className="font-medium text-muted-foreground capitalize">
                        {k.replace(/_/g, " ")}
                      </span>
                      <span className="text-foreground font-mono text-xs">
                        {typeof v === "number" ? v.toFixed(4) : String(v)}
                      </span>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">No metrics available</p>
                )}
              </div>

              {/* Categories */}
              {selectedModelCategories && (
                <div className="col-span-full space-y-2">
                  <h3 className="text-sm font-semibold text-green-600">
                    Categories ({selectedModelCategories.categories_count})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedModelCategories.categories.map((cat: string) => (
                      <span
                        key={cat}
                        className="px-2 py-1 bg-muted text-xs rounded-md font-mono"
                      >
                        {cat}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Assignments */}
              <div className="col-span-full space-y-2">
                <h3 className="text-sm font-semibold text-purple-600">
                  Assignments
                </h3>
                {getModelAssignments(selectedModel.version).length > 0 ? (
                  <div className="space-y-2">
                    {getModelAssignments(selectedModel.version).map((assignment) => (
                      <div
                        key={assignment.id}
                        className="p-3 bg-muted/30 rounded-md text-sm"
                      >
                        <div className="flex justify-between">
                          <span className="font-medium">
                            {assignment.source_app_slug} → {assignment.target_app_slug}
                          </span>
                          <span className="text-muted-foreground text-xs">
                            {new Date(assignment.assigned_at).toLocaleString("en-IN")}
                          </span>
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          Assigned by: {assignment.assigned_by_username}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No assignments yet</p>
                )}
              </div>
            </div>
          ) : (
            <div className="flex justify-center items-center text-muted-foreground py-6">
              <Loader2 className="animate-spin mr-2" /> Loading details...
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Assign Model Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign Model to App</DialogTitle>
            <DialogDescription>
              Select the target app to assign this model.
            </DialogDescription>
          </DialogHeader>

          {modelToAssign && (
            <div className="space-y-4 mt-4">
              <div className="p-3 bg-muted/30 rounded-md">
                <div className="text-sm">
                  <span className="font-semibold">Model:</span>{" "}
                  {modelToAssign.version}
                </div>
                <div className="text-sm text-muted-foreground">
                  <span className="font-semibold">Current App:</span>{" "}
                  {modelToAssign.app_slug}
                </div>
              </div>

              <div className="space-y-1">
                <Label htmlFor="target_app">Target App</Label>
                <select
                  id="target_app"
                  value={selectedTargetSlug}
                  onChange={(e) => setSelectedTargetSlug(e.target.value)}
                  className="w-full border rounded-md p-2 bg-background text-foreground"
                >
                  <option value="">Select Target App</option>
                  {appSlugs.map((app) => (
                    <option key={app.id} value={app.slug}>
                      {app.slug}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button
                  className="bg-red-600 hover:bg-red-700 text-white"
                  onClick={() => {
                    setAssignDialogOpen(false);
                    setSelectedTargetSlug("");
                  }}
                >
                  <X className="w-4 h-4 mr-1" /> Cancel
                </Button>
                <Button
                  className="bg-green-600 hover:bg-green-700 text-white"
                  onClick={assignModel}
                  disabled={assignLoading || !selectedTargetSlug}
                >
                  {assignLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                      Assigning...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4 mr-1" /> Assign
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}