/**
 * PaywallCard, from the Honest Paywall Kit by Devon Okafor.
 * Original presentational component written for this prototype sample.
 * No state, no data fetching, no side effects: props in, markup out.
 * The design rule of the kit: total price, renewal date, and the restore
 * path are all visible before the subscribe action.
 */

export type PaywallCardProps = {
  productName: string;
  totalPrice: string;
  renewalDate: string;
  trialDays?: number;
  benefits: string[];
  onSubscribe?: () => void;
  onRestore?: () => void;
  onClose?: () => void;
};

export function PaywallCard(props: PaywallCardProps) {
  const {
    productName,
    totalPrice,
    renewalDate,
    trialDays,
    benefits,
    onSubscribe,
    onRestore,
    onClose,
  } = props;

  return (
    <section aria-label={`${productName} subscription`} data-findui-kit="paywall-pro">
      <header>
        <h2>{productName} Pro</h2>
        {onClose ? (
          <button type="button" onClick={onClose} aria-label="Close paywall">
            Close
          </button>
        ) : null}
      </header>

      <ul>
        {benefits.map((benefit) => (
          <li key={benefit}>{benefit}</li>
        ))}
      </ul>

      <p>
        Total today: {totalPrice}.{" "}
        {trialDays
          ? `Free for ${trialDays} days, then renews on ${renewalDate} at ${totalPrice}. `
          : `Renews on ${renewalDate} at ${totalPrice}. `}
        Cancel any time before the renewal date and you pay nothing more.
      </p>

      <button type="button" onClick={onSubscribe}>
        Subscribe for {totalPrice}
      </button>

      {onRestore ? (
        <button type="button" onClick={onRestore}>
          Restore purchase
        </button>
      ) : null}

      <footer>
        <small>
          Kit by Devon Okafor via FindUI.
          {" "}
          <a href="https://findui.com/creators/devon-okafor/honest-paywall-kit">
            Attribution
          </a>
        </small>
      </footer>
    </section>
  );
}

export default PaywallCard;
