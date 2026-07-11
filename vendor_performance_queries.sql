/* 1. INITIAL DATA EXPLORATION */
SELECT COUNT(*) FROM sales;                 -- 12,825,363 rows
SELECT COUNT(*) FROM purchases;             -- 2,372,474 rows

SELECT * FROM purchases LIMIT 5;
SELECT * FROM purchase_prices LIMIT 5;
SELECT * FROM vendor_invoice LIMIT 5;
SELECT * FROM sales LIMIT 5;

/* 2. STANDALONE SUMMARY QUERIES (used while designing the final table) */
-- Freight summary: total shipping cost per vendor
SELECT VendorNumber, SUM(Freight) AS FreightCost
FROM vendor_invoice
GROUP BY VendorNumber;

-- Purchase summary: qty/dollars per vendor+brand, invalid zero-price rows removed
SELECT
    p.VendorNumber, p.VendorName, p.Brand,
    pp.Volume, pp.Price AS ActualPrice,
    SUM(p.Quantity) AS TotalPurchaseQuantity,
    SUM(p.Dollars)  AS TotalPurchaseDollars
FROM purchases p
JOIN purchase_prices pp ON p.Brand = pp.Brand
WHERE p.PurchasePrice > 0
GROUP BY p.VendorNumber, p.VendorName, p.Brand
ORDER BY TotalPurchaseDollars;

-- Sales summary: aggregated sales metrics per vendor+brand
SELECT
    VendorNo, Brand,
    SUM(SalesDollars)  AS TotalSalesDollars,
    SUM(SalesPrice)    AS TotalSalesPrice,
    SUM(SalesQuantity) AS TotalSalesQuantity,
    SUM(ExciseTax)     AS TotalExciseTax
FROM sales
GROUP BY VendorNo, Brand
ORDER BY TotalSalesDollars;

/* 3. OPTIMIZED FINAL TABLE BUILD (aggregate-before-join) */
DROP TABLE IF EXISTS vendor_sales_summary;

CREATE TABLE vendor_sales_summary AS
WITH FreightSummary AS (
    SELECT VendorNumber, SUM(Freight) AS FreightCost
    FROM vendor_invoice
    GROUP BY VendorNumber
),
PurchaseSummary AS (
    SELECT
        p.VendorNumber, p.VendorName, p.Brand, p.Description,
        pp.Volume, pp.Price AS ActualPrice, pp.PurchasePrice,
        SUM(p.Quantity) AS TotalPurchaseQuantity,
        SUM(p.Dollars)  AS TotalPurchaseDollars
    FROM purchases p
    JOIN purchase_prices pp ON p.Brand = pp.Brand
    WHERE p.PurchasePrice > 0
    GROUP BY p.VendorNumber, p.VendorName, p.Brand, p.Description,
             pp.Volume, pp.Price, pp.PurchasePrice
),
SalesSummary AS (
    SELECT
        VendorNo, Brand,
        SUM(SalesDollars)   AS TotalSalesDollars,
        SUM(SalesPrice)     AS TotalSalesPrice,
        SUM(SalesQuantity)  AS TotalSalesQuantity,
        SUM(ExciseTax)      AS TotalExciseTax
    FROM sales
    GROUP BY VendorNo, Brand
)
SELECT
    ps.VendorNumber, ps.VendorName, ps.Brand, ps.Description,
    ps.Volume, ps.PurchasePrice, ps.ActualPrice,
    ps.TotalPurchaseQuantity, ps.TotalPurchaseDollars,
    ss.TotalSalesQuantity, ss.TotalSalesDollars,
    ss.TotalSalesPrice, ss.TotalExciseTax,
    fs.FreightCost
FROM PurchaseSummary ps
LEFT JOIN SalesSummary  ss ON ps.VendorNumber = ss.VendorNo AND ps.Brand = ss.Brand
LEFT JOIN FreightSummary fs ON ps.VendorNumber = fs.VendorNumber;

CREATE INDEX idx_vss_vendor_brand ON vendor_sales_summary(VendorNumber, Brand);
