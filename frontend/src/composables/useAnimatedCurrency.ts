import { computed, toValue, type MaybeRefOrGetter } from "vue";
import { TransitionPresets, useTransition } from "@vueuse/core";
import Decimal from "decimal.js";
import { formatCurrency } from "@/lib/money";

/**
 * Anima un valor monetario "corriendo" entre su valor anterior y el nuevo
 * (D-54: animación de cálculos del MVP, vía `useTransition` de VueUse).
 * Es solo el efecto visual del contador — el dato real sigue siendo el
 * `Decimal` fuente; los frames intermedios pasan por número flotante, pero
 * eso nunca se guarda ni se valida, solo se ve un instante en pantalla.
 */
export function useAnimatedCurrency(source: MaybeRefOrGetter<Decimal>) {
  const numberSource = computed(() => toValue(source).toNumber());
  const animated = useTransition(numberSource, {
    duration: 400,
    easing: TransitionPresets.easeOutExpo,
  });
  return computed(() => formatCurrency(animated.value));
}
