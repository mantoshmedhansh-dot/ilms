import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Return & Refund Policy | Aquapurite',
  description: 'Learn about Aquapurite return and refund policy. Easy 7-day returns on eligible products with hassle-free refund process.',
  openGraph: {
    title: 'Return & Refund Policy | Aquapurite',
    description: 'Learn about Aquapurite return and refund policy. Easy 7-day returns on eligible products with hassle-free refund process.',
    type: 'website',
  },
};

export default function ReturnPolicyPage() {
  return (
    <div className="container mx-auto px-4 py-12 md:py-16">
      <article className="max-w-4xl mx-auto">
        <header className="mb-8">
          <h1 className="text-3xl md:text-4xl font-bold mb-4">Return & Refund Policy</h1>
          <p className="text-muted-foreground">Last updated: January 2026</p>
        </header>

        <div className="prose prose-lg max-w-none prose-headings:font-bold prose-a:text-primary">
          <p>
            At Aquapurite, we strive to ensure complete customer satisfaction with every purchase.
            If you are not entirely satisfied with your purchase, we&apos;re here to help.
          </p>

          <h2>Return Eligibility</h2>
          <p>You may return most new, unopened items within 7 days of delivery for a full refund. We also accept returns of defective items within the warranty period.</p>

          <h3>Conditions for Return</h3>
          <ul>
            <li>Products must be unused and in original packaging</li>
            <li>Products must include all accessories, manuals, and warranty cards</li>
            <li>Products should not have any physical damage caused by misuse</li>
            <li>Return request must be initiated within 7 days of delivery</li>
          </ul>

          <h3>Non-Returnable Items</h3>
          <ul>
            <li>Installed products (unless defective)</li>
            <li>Products with broken seals or missing parts</li>
            <li>Consumable spare parts (filters, membranes) once opened</li>
            <li>Products damaged due to improper handling or installation</li>
          </ul>

          <h2>How to Initiate a Return</h2>
          <ol>
            <li>Log in to your Aquapurite account and go to &quot;My Orders&quot;</li>
            <li>Select the order containing the item you wish to return</li>
            <li>Click on &quot;Request Return&quot; and provide the reason for return</li>
            <li>Our team will review your request within 24-48 hours</li>
            <li>Once approved, schedule a pickup or drop the item at our service center</li>
          </ol>

          <h2>Refund Process</h2>
          <p>Once we receive and inspect the returned item, we will notify you about the status of your refund.</p>

          <h3>Refund Timeline</h3>
          <ul>
            <li><strong>Credit/Debit Card:</strong> 5-7 business days</li>
            <li><strong>UPI/Net Banking:</strong> 3-5 business days</li>
            <li><strong>Wallet:</strong> 1-2 business days</li>
            <li><strong>EMI:</strong> Refund will be processed as per bank terms</li>
          </ul>

          <h3>Refund Amount</h3>
          <p>The refund amount will include the product price. Shipping charges are non-refundable unless the return is due to our error or a defective product.</p>

          <h2>Replacement Policy</h2>
          <p>If you received a defective or damaged product, you can request a replacement instead of a refund. Replacements are subject to stock availability. If the product is not available, a full refund will be processed.</p>

          <h2>Cancellation Policy</h2>
          <p>Orders can be cancelled before shipment for a full refund. Once the product is shipped, it cannot be cancelled but can be returned after delivery as per our return policy.</p>

          <h2>Contact Us</h2>
          <p>If you have any questions about our return and refund policy, please contact us:</p>
          <ul>
            <li>Email: <a href="mailto:support@aquapurite.com">support@aquapurite.com</a></li>
            <li>Phone: 1800-123-4567 (Toll Free)</li>
            <li>Visit: <a href="/support">Support Page</a></li>
          </ul>
        </div>
      </article>
    </div>
  );
}
