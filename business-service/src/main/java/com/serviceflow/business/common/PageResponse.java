package com.serviceflow.business.common;

import java.util.List;

/** Stable generic page contract for read APIs. */
public record PageResponse<T>(
        long page,
        long size,
        long total,
        List<T> items
) {
}
