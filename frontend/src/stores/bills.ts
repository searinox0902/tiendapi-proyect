import { ref } from "vue";
import { defineStore } from "pinia";
import type { IBill, IBillDetail, IBillFilters, IBillSummary } from "@/api/bills/bills.types";
import { billsApi } from "@/api/bills/bills.api";
import { ensureMinDuration } from "@/lib/async";

const SKELETON_MIN_DURATION_MS = 340;

export const useBillsStore = defineStore("bills", () => {

  const bills = ref<IBill[]>([]);
  const total = ref(0);
  const isLoading = ref(false);
  const hasError = ref(false);

const summary = ref<IBillSummary | null>(null);
  const isLoadingSummary = ref(false);

  async function fetchBills(filters: IBillFilters): Promise<void> {
    isLoading.value = true;
    hasError.value = false;
    try {
      const { data } = await ensureMinDuration(
        billsApi.getBills(filters),
        SKELETON_MIN_DURATION_MS,
      );
      bills.value = data.items;
      total.value = data.total;
    } catch (error) {
      console.error("Fetch bills failed:", error);
      hasError.value = true;
      bills.value = [];
      total.value = 0;
      throw error;
    } finally {
      isLoading.value = false;
    }
  }

  async function fetchSummary(filters: IBillFilters): Promise<void> {
    isLoadingSummary.value = true;
    try {
      const { data } = await billsApi.getSummary(filters);
      summary.value = data;
    } catch (error) {
      console.error("Fetch bills summary failed:", error);
      summary.value = null;
      throw error;
    } finally {
      isLoadingSummary.value = false;
    }
  }

  const detail = ref<IBillDetail | null>(null);
  const isLoadingDetail = ref(false);
  const hasDetailError = ref(false);

  async function fetchDetail(billId: string): Promise<void> {
    isLoadingDetail.value = true;
    hasDetailError.value = false;
    detail.value = null;
    try {
      const { data } = await ensureMinDuration(
        billsApi.getDetail(billId),
        SKELETON_MIN_DURATION_MS,
      );
      detail.value = data;
    } catch (error) {
      console.error("Fetch bill detail failed:", error);
      hasDetailError.value = true;
      throw error;
    } finally {
      isLoadingDetail.value = false;
    }
  }

  async function voidBill(billId: string, reason: string): Promise<void> {
    const { data } = await billsApi.void(billId, { reason });
    detail.value = data;
  }

  return {
    bills, total, isLoading, hasError, summary, isLoadingSummary,
    fetchBills, fetchSummary,
    detail, isLoadingDetail, hasDetailError, fetchDetail, voidBill,
  };
});
